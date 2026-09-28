import Foundation

struct QuizQuestion: Identifiable {
    enum Kind {
        /// The example sentence with the word blanked out.
        case fillBlank
        /// "Instead of saying '…', a lead would say…"
        case sayItBetter
    }

    let id = UUID()
    let kind: Kind
    let answer: Word
    let options: [Word]
}

enum QuizBuilder {
    /// Builds a round of alternating question types from `pool`, drawing distractors from `allWords`.
    static func makeRound(pool: [Word], allWords: [Word], count: Int = 10) -> [QuizQuestion] {
        guard !pool.isEmpty, allWords.count >= 4 else { return [] }

        var answers: [Word] = []
        while answers.count < count {
            answers.append(contentsOf: pool.shuffled())
        }

        return answers.prefix(count).enumerated().map { index, answer in
            QuizQuestion(
                kind: index.isMultiple(of: 2) ? .fillBlank : .sayItBetter,
                answer: answer,
                options: (distractors(for: answer, from: allWords) + [answer]).shuffled()
            )
        }
    }

    /// Three wrong options, preferring the same part of speech so the grammar doesn't give it away.
    static func distractors(for answer: Word, from allWords: [Word]) -> [Word] {
        let others = allWords.filter { $0.word != answer.word }
        let samePOS = others.filter { $0.partOfSpeech == answer.partOfSpeech }.shuffled()
        let rest = others.filter { $0.partOfSpeech != answer.partOfSpeech }.shuffled()
        return Array((samePOS + rest).prefix(3))
    }

    static func message(score: Int, total: Int) -> String {
        let percent = total == 0 ? 0 : Double(score) / Double(total)
        switch percent {
        case 0.9...:
            return "Excellent. You'd sound sharp in any design review."
        case 0.7..<0.9:
            return "Strong round. A couple more passes and these will be second nature."
        case 0.5..<0.7:
            return "Good progress. Revisit the ones you missed in Learn."
        default:
            return "Early days. Every round makes these stick a little more."
        }
    }
}
