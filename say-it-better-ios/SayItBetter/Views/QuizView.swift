import SwiftUI
import SwiftData

struct QuizView: View {
    @Environment(WordStore.self) private var store
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \QuizResult.date, order: .reverse) private var history: [QuizResult]

    @State private var questions: [QuizQuestion] = []
    @State private var index = 0
    @State private var selected: Word?
    @State private var score = 0
    @State private var finished = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                CategoryChips()
                ScrollView {
                    Group {
                        if finished {
                            results
                        } else if questions.indices.contains(index) {
                            questionView(questions[index])
                        } else {
                            ContentUnavailableView("Not enough words", systemImage: "questionmark.circle",
                                                   description: Text("A quiz needs at least four words to choose from."))
                        }
                    }
                    .padding()
                }
            }
            .background(Theme.background)
            .navigationTitle("Quiz")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if !finished, !questions.isEmpty {
                    ToolbarItem(placement: .topBarLeading) {
                        Text("\(index + 1)/\(questions.count) · \(score) right")
                            .font(Theme.monoSmall)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .settingsToolbar()
            .onAppear {
                if questions.isEmpty { newRound() }
            }
            .onChange(of: store.categoryFilter) { newRound() }
        }
    }

    // MARK: - Question

    private func questionView(_ question: QuizQuestion) -> some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 10) {
                SectionLabel(question.kind == .fillBlank ? "Fill the blank" : "Say it better")
                switch question.kind {
                case .fillBlank:
                    Text(question.answer.blankedExample)
                        .font(Theme.serif(.title3, weight: .regular))
                case .sayItBetter:
                    (Text("Instead of saying ")
                        + Text("“\(question.answer.insteadOf)”").italic()
                        + Text(", a lead would say…"))
                        .font(Theme.serif(.title3, weight: .regular))
                }
            }
            .fixedSize(horizontal: false, vertical: true)
            .card()

            VStack(spacing: 10) {
                ForEach(question.options) { option in
                    optionButton(option, answer: question.answer)
                }
            }

            if selected != nil {
                VStack(alignment: .leading, spacing: 8) {
                    HStack(alignment: .firstTextBaseline) {
                        Text(question.answer.word)
                            .font(Theme.serif(.title2))
                        Text(question.answer.partOfSpeech)
                            .font(Theme.monoSmall)
                            .foregroundStyle(.secondary)
                        Spacer()
                        HearItButton(text: question.answer.word)
                    }
                    Text(question.answer.definition)
                    HighlightedExample(word: question.answer, font: .subheadline)
                        .foregroundStyle(.secondary)
                }
                .card()

                Button {
                    next()
                } label: {
                    Text(index + 1 < questions.count ? "Next question" : "See results")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
            }
        }
        .animation(.easeInOut(duration: 0.2), value: selected)
    }

    private func optionButton(_ option: Word, answer: Word) -> some View {
        let isAnswer = option.word == answer.word
        let isPicked = option.word == selected?.word
        let answered = selected != nil

        let tint: Color? = {
            guard answered else { return nil }
            if isAnswer { return .green }
            if isPicked { return .red }
            return nil
        }()

        return Button {
            guard selected == nil else { return }
            selected = option
            if isAnswer { score += 1 }
        } label: {
            HStack {
                Text(option.word)
                    .font(Theme.serif(.headline, weight: .medium))
                Spacer()
                if answered, isAnswer {
                    Image(systemName: "checkmark.circle.fill")
                } else if answered, isPicked {
                    Image(systemName: "xmark.circle.fill")
                }
            }
            .padding()
            .frame(maxWidth: .infinity)
            .foregroundStyle(tint ?? .primary)
            .background(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(tint.map { $0.opacity(0.15) } ?? Theme.surface)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .strokeBorder(tint ?? Theme.hairline, lineWidth: tint == nil ? 0.5 : 1.5)
            )
            .opacity(answered && tint == nil ? 0.55 : 1)
        }
        .buttonStyle(.plain)
        .disabled(answered)
    }

    // MARK: - Results

    private var results: some View {
        VStack(spacing: 20) {
            VStack(spacing: 8) {
                Text("\(score) / \(questions.count)")
                    .font(Theme.serif(.largeTitle))
                Text(QuizBuilder.message(score: score, total: questions.count))
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 24)
            .frame(maxWidth: .infinity)
            .card()

            Button {
                newRound()
            } label: {
                Text("New round").frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)

            if !history.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    SectionLabel("Recent rounds")
                    ForEach(history.prefix(5)) { result in
                        HStack {
                            Text(result.date, format: .dateTime.month().day().hour().minute())
                            Text(result.category ?? "All")
                                .font(Theme.monoSmall)
                                .foregroundStyle(.secondary)
                            Spacer()
                            Text("\(result.score)/\(result.total)")
                                .font(Theme.mono)
                        }
                        .font(.subheadline)
                    }
                }
                .card()
            }
        }
    }

    // MARK: - Flow

    private func newRound() {
        questions = QuizBuilder.makeRound(pool: store.filteredWords, allWords: store.words)
        index = 0
        selected = nil
        score = 0
        finished = false
    }

    private func next() {
        selected = nil
        if index + 1 < questions.count {
            index += 1
        } else {
            finished = true
            modelContext.insert(QuizResult(score: score, total: questions.count, category: store.categoryFilter))
        }
    }
}

#Preview {
    QuizView()
        .environment(WordStore())
        .environment(DeepDiveService())
        .modelContainer(for: QuizResult.self, inMemory: true)
}
