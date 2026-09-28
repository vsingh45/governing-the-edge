import Foundation

/// Outside references for a word, opened in Safari from the Deep dive sheet.
enum ReferenceLinks {
    struct Link: Identifiable {
        let title: String
        let url: URL
        var id: String { title }
    }

    static func links(for word: String) -> [Link] {
        let lower = word.lowercased()
        let dashed = lower.replacingOccurrences(of: " ", with: "-")
        let encoded = lower.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? lower

        let candidates: [(String, String)] = [
            ("Oxford Learner's Dictionaries", "https://www.oxfordlearnersdictionaries.com/definition/english/\(dashed)"),
            ("Etymonline", "https://www.etymonline.com/word/\(encoded)"),
            ("YouGlish", "https://youglish.com/pronounce/\(encoded)/english"),
        ]
        return candidates.compactMap { title, string in
            URL(string: string).map { Link(title: title, url: $0) }
        }
    }
}
