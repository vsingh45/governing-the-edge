import Foundation
import Observation

/// Shared app state: every word, which ones are known, and the category filter that the
/// Learn, Quiz and All words tabs share.
@Observable
final class WordStore {
    let words: [Word]
    /// Categories in the order they first appear in `words.json`.
    let categories: [String]

    private(set) var known: Set<String>
    /// nil means "All".
    var categoryFilter: String?

    private let sync: KnownWordsSync

    init(words: [Word] = WordLoader.load(), sync: KnownWordsSync = KnownWordsSync()) {
        self.words = words
        var seen = Set<String>()
        self.categories = words.map(\.category).filter { seen.insert($0).inserted }
        self.sync = sync
        self.known = sync.load()
        sync.onRemoteChange = { [weak self] remote in
            self?.known = remote
        }
    }

    var isCloudSyncAvailable: Bool { sync.isCloudAvailable }

    /// Words in the current category filter.
    var filteredWords: [Word] {
        guard let categoryFilter else { return words }
        return words.filter { $0.category == categoryFilter }
    }

    /// Every known word, A–Z, regardless of the filter.
    var knownWords: [Word] {
        words
            .filter { known.contains($0.word) }
            .sorted { $0.word.localizedCaseInsensitiveCompare($1.word) == .orderedAscending }
    }

    func isKnown(_ word: Word) -> Bool {
        known.contains(word.word)
    }

    func setKnown(_ isKnown: Bool, for word: Word) {
        if isKnown {
            known.insert(word.word)
        } else {
            known.remove(word.word)
        }
        sync.save(known)
    }

    func resetProgress() {
        known.removeAll()
        sync.save(known)
    }
}
