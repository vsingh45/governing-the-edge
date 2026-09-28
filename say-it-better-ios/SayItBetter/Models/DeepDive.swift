import Foundation

/// The in-depth explanation shown in the Deep dive sheet. The same shape comes from the
/// bundled `deepdive.json` and from the personal backend, so decoding is lenient: a live
/// response that omits a field still renders.
struct DeepDive: Codable, Equatable {
    struct FamilyMember: Codable, Hashable {
        var word: String
        var meaning: String
    }

    struct Comparison: Codable, Hashable {
        var word: String
        var difference: String
    }

    struct Example: Codable, Hashable {
        var setting: String
        var sentence: String
    }

    var word: String
    var pronunciation: String
    var partOfSpeech: String
    var meaning: String
    var origin: String
    var family: [FamilyMember]
    var collocations: [String]
    var compare: [Comparison]
    var mistake: String
    var examples: [Example]
    var tip: String

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        word = try c.decode(String.self, forKey: .word)
        pronunciation = try c.decodeIfPresent(String.self, forKey: .pronunciation) ?? ""
        partOfSpeech = try c.decodeIfPresent(String.self, forKey: .partOfSpeech) ?? ""
        meaning = try c.decodeIfPresent(String.self, forKey: .meaning) ?? ""
        origin = try c.decodeIfPresent(String.self, forKey: .origin) ?? ""
        family = try c.decodeIfPresent([FamilyMember].self, forKey: .family) ?? []
        collocations = try c.decodeIfPresent([String].self, forKey: .collocations) ?? []
        compare = try c.decodeIfPresent([Comparison].self, forKey: .compare) ?? []
        mistake = try c.decodeIfPresent(String.self, forKey: .mistake) ?? ""
        examples = try c.decodeIfPresent([Example].self, forKey: .examples) ?? []
        tip = try c.decodeIfPresent(String.self, forKey: .tip) ?? ""
    }
}

/// Feedback on a sentence the user wrote with the word, from the backend's `/checkSentence`.
struct SentenceFeedback: Codable, Equatable {
    /// "good", "almost" or "off".
    var verdict: String
    var feedback: String
    var improved: String?
}
