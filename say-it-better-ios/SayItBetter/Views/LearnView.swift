import SwiftUI

struct LearnView: View {
    @Environment(WordStore.self) private var store

    /// Word ids still to go this round, front first.
    @State private var queue: [String] = []
    @State private var roundSize = 0
    @State private var started = false
    @State private var deepDiveWord: Word?

    private var current: Word? {
        guard let id = queue.first else { return nil }
        return store.words.first { $0.word == id }
    }

    private var unknownPool: [Word] {
        store.filteredWords.filter { !store.isKnown($0) }
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                CategoryChips()
                if let current {
                    LearnCard(word: current) { deepDiveWord = current }
                    actionBar(for: current)
                } else {
                    completion
                }
            }
            .background(Theme.background)
            .navigationTitle("Learn")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if current != nil {
                    ToolbarItem(placement: .topBarLeading) {
                        Text("\(roundSize - queue.count + 1) of \(roundSize)")
                            .font(Theme.monoSmall)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .settingsToolbar()
            .sheet(item: $deepDiveWord) { DeepDiveSheet(word: $0) }
            .onAppear {
                if !started { startRound() }
            }
            .onChange(of: store.categoryFilter) { startRound() }
            .onChange(of: store.known) {
                // Marked known elsewhere (All words, another device): drop it from the round.
                queue.removeAll { id in store.known.contains(id) }
            }
        }
    }

    private func actionBar(for word: Word) -> some View {
        HStack(spacing: 12) {
            Button {
                stillLearning()
            } label: {
                Text("Still learning")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)

            Button {
                store.setKnown(true, for: word)
                queue.removeAll { $0 == word.word }
            } label: {
                Text("I know this")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
        }
        .controlSize(.large)
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(.bar)
    }

    @ViewBuilder
    private var completion: some View {
        let remaining = unknownPool.count
        ContentUnavailableView {
            Label(remaining == 0 ? "Every word here is known" : "Round complete",
                  systemImage: remaining == 0 ? "checkmark.seal" : "flag.checkered")
        } description: {
            if remaining == 0 {
                Text("Pick another category, or use Relearn in My words to bring a word back.")
            } else {
                Text("\(remaining) word\(remaining == 1 ? "" : "s") still in progress. Go again while they're fresh.")
            }
        } actions: {
            if remaining > 0 {
                Button("Start again") { startRound() }
                    .buttonStyle(.borderedProminent)
            }
        }
        .frame(maxHeight: .infinity)
    }

    private func startRound() {
        started = true
        queue = unknownPool.shuffled().map(\.word)
        roundSize = queue.count
    }

    /// Requeue the current card about three cards later.
    private func stillLearning() {
        guard !queue.isEmpty else { return }
        let id = queue.removeFirst()
        queue.insert(id, at: min(3, queue.count))
    }
}

/// Everything about a word at once: no reveal tap.
private struct LearnCard: View {
    let word: Word
    let onGoDeeper: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    WordMeta(word: word)
                    HStack(alignment: .firstTextBaseline) {
                        Text(word.word)
                            .font(Theme.headword)
                            .minimumScaleFactor(0.6)
                            .lineLimit(2)
                        Spacer(minLength: 8)
                        HearItButton(text: word.word)
                    }
                    Text(word.pronunciation)
                        .font(Theme.mono)
                        .foregroundStyle(.secondary)
                }

                Text(word.definition)
                    .font(.title3)
                    .fixedSize(horizontal: false, vertical: true)

                VStack(alignment: .leading, spacing: 8) {
                    SectionLabel("Goes with")
                    PhraseChips(phrases: word.goesWith)
                }

                VStack(alignment: .leading, spacing: 8) {
                    SectionLabel("In a sentence")
                    HighlightedExample(word: word, font: Theme.serif(.body, weight: .regular))
                }

                InsteadOfSwap(word: word)
                    .card()

                Button(action: onGoDeeper) {
                    Label("Go deeper", systemImage: "text.magnifyingglass")
                }
                .buttonStyle(.borderless)
            }
            .card()
            .padding()
            .id(word.word)
            .transition(.opacity)
        }
        .animation(.easeInOut(duration: 0.2), value: word.word)
    }
}

#Preview {
    LearnView()
        .environment(WordStore())
        .environment(DeepDiveService())
}
