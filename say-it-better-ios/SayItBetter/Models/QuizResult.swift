import Foundation
import SwiftData

/// One finished quiz round, kept locally so the end screen can show recent history.
@Model
final class QuizResult {
    var date: Date
    var score: Int
    var total: Int
    /// The category filter in effect, or nil for all words.
    var category: String?

    init(date: Date = .now, score: Int, total: Int, category: String?) {
        self.date = date
        self.score = score
        self.total = total
        self.category = category
    }
}
