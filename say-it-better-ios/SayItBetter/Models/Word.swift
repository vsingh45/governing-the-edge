import Foundation

/// One vocabulary entry, decoded from the bundled `words.json`.
struct Word: Codable, Identifiable, Hashable {
    let word: String
    let pronunciation: String
    let partOfSpeech: String
    let category: String
    let definition: String
    let example: String
    let insteadOf: String
    let goesWith: [String]

    var id: String { word }
}

enum WordLoader {
    static func load(resource: String = "words", bundle: Bundle = .main) -> [Word] {
        guard let url = bundle.url(forResource: resource, withExtension: "json") else {
            assertionFailure("\(resource).json is missing from the app bundle")
            return []
        }
        do {
            return try JSONDecoder().decode([Word].self, from: Data(contentsOf: url))
        } catch {
            assertionFailure("Could not decode \(resource).json: \(error)")
            return []
        }
    }
}

// MARK: - Example sentence helpers

extension Word {
    /// A run of text in the example sentence; `emphasised` is true for the `[bracketed]` target word.
    struct ExampleSegment: Hashable {
        let text: String
        let emphasised: Bool
    }

    var exampleSegments: [ExampleSegment] {
        var segments: [ExampleSegment] = []
        var current = ""
        var inside = false
        for character in example {
            if character == "[", !inside {
                if !current.isEmpty { segments.append(.init(text: current, emphasised: false)) }
                current = ""
                inside = true
            } else if character == "]", inside {
                segments.append(.init(text: current, emphasised: true))
                current = ""
                inside = false
            } else {
                current.append(character)
            }
        }
        if !current.isEmpty { segments.append(.init(text: current, emphasised: false)) }
        return segments
    }

    /// The example with the target word replaced by a blank, for fill-the-blank questions.
    var blankedExample: String {
        exampleSegments.map { $0.emphasised ? "_____" : $0.text }.joined()
    }

    /// The example with the brackets removed.
    var plainExample: String {
        exampleSegments.map(\.text).joined()
    }

    /// True when `text` contains this word (or a simple inflection of it).
    func isUsed(in text: String) -> Bool {
        let haystack = text.lowercased()
        let needle = word.lowercased()
        if haystack.contains(needle) { return true }
        // Allow inflections like "prioritized", "deferred", "caveats" by matching the stem.
        let stem = needle.count > 5 ? String(needle.dropLast(2)) : needle
        return haystack.contains(stem)
    }
}
