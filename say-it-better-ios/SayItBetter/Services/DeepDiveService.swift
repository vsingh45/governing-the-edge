import Foundation
import Observation

/// Supplies Deep dive content. Prefers the personal backend (Claude Agent SDK on the user's Mac)
/// when it is configured and reachable, and falls back to the bundled `deepdive.json` otherwise.
@MainActor
@Observable
final class DeepDiveService {
    enum Source: Equatable {
        case live
        case bundled
    }

    enum Reachability: Equatable {
        case notConfigured
        case checking
        case reachable
        case unreachable
    }

    enum ServiceError: LocalizedError {
        case noBackend
        case badResponse(Int)

        var errorDescription: String? {
            switch self {
            case .noBackend:
                return "Sentence feedback needs your backend running. Set its URL in Settings."
            case .badResponse(let status):
                return "The backend answered with HTTP \(status)."
            }
        }
    }

    private static let backendKey = "backendURL"

    var backendURLString: String {
        didSet {
            UserDefaults.standard.set(backendURLString, forKey: Self.backendKey)
            liveCache.removeAll()
        }
    }

    private(set) var reachability: Reachability = .notConfigured

    private let bundled: [String: DeepDive]
    @ObservationIgnored private var liveCache: [String: DeepDive] = [:]
    private let session: URLSession

    init(bundle: Bundle = .main) {
        backendURLString = UserDefaults.standard.string(forKey: Self.backendKey) ?? ""
        bundled = Self.loadBundled(bundle: bundle)

        let config = URLSessionConfiguration.default
        // Claude can take a while to write a full deep dive.
        config.timeoutIntervalForRequest = 120
        session = URLSession(configuration: config)
    }

    var backendURL: URL? {
        let trimmed = backendURLString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard
            !trimmed.isEmpty,
            let url = URL(string: trimmed),
            let scheme = url.scheme?.lowercased(),
            scheme == "http" || scheme == "https",
            url.host != nil
        else { return nil }
        return url
    }

    // MARK: - Reachability

    /// Pings `{backend}/health` with a short timeout.
    func checkReachability() async {
        guard let backendURL else {
            reachability = .notConfigured
            return
        }
        reachability = .checking
        var request = URLRequest(url: backendURL.appendingPathComponent("health"))
        request.timeoutInterval = 4
        do {
            let (_, response) = try await session.data(for: request)
            let ok = (response as? HTTPURLResponse)?.statusCode == 200
            reachability = ok ? .reachable : .unreachable
        } catch {
            reachability = .unreachable
        }
    }

    // MARK: - Deep dive

    func bundledDeepDive(for word: String) -> DeepDive? {
        bundled[word.lowercased()]
    }

    /// Live content when the backend answers; bundled content otherwise.
    func deepDive(for word: String) async -> (DeepDive, Source)? {
        if let cached = liveCache[word] {
            return (cached, .live)
        }
        if backendURL != nil, reachability != .reachable {
            // It may have come up since launch; a quick ping beats a two-minute request timeout.
            await checkReachability()
        }
        if reachability == .reachable {
            do {
                let live = try await fetchLive(word)
                liveCache[word] = live
                reachability = .reachable
                return (live, .live)
            } catch {
                reachability = .unreachable
            }
        }
        return bundledDeepDive(for: word).map { ($0, Source.bundled) }
    }

    private func fetchLive(_ word: String) async throws -> DeepDive {
        guard let backendURL else { throw ServiceError.noBackend }
        var components = URLComponents(url: backendURL.appendingPathComponent("deepdive"), resolvingAgainstBaseURL: false)
        components?.queryItems = [URLQueryItem(name: "word", value: word)]
        guard let url = components?.url else { throw ServiceError.noBackend }

        let (data, response) = try await session.data(from: url)
        try Self.check(response)
        return try JSONDecoder().decode(DeepDive.self, from: data)
    }

    // MARK: - Sentence feedback

    func checkSentence(_ sentence: String, word: String) async throws -> SentenceFeedback {
        guard let backendURL else { throw ServiceError.noBackend }
        var request = URLRequest(url: backendURL.appendingPathComponent("checkSentence"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["word": word, "sentence": sentence])

        let (data, response) = try await session.data(for: request)
        try Self.check(response)
        reachability = .reachable
        return try JSONDecoder().decode(SentenceFeedback.self, from: data)
    }

    // MARK: - Helpers

    private static func check(_ response: URLResponse) throws {
        guard let status = (response as? HTTPURLResponse)?.statusCode else { return }
        guard (200..<300).contains(status) else { throw ServiceError.badResponse(status) }
    }

    private static func loadBundled(bundle: Bundle) -> [String: DeepDive] {
        guard
            let url = bundle.url(forResource: "deepdive", withExtension: "json"),
            let data = try? Data(contentsOf: url),
            let entries = try? JSONDecoder().decode([DeepDive].self, from: data)
        else {
            assertionFailure("deepdive.json is missing or malformed")
            return [:]
        }
        return Dictionary(entries.map { ($0.word.lowercased(), $0) }, uniquingKeysWith: { first, _ in first })
    }
}
