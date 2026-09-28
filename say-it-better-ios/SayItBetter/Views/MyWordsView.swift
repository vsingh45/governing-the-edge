import SwiftUI

struct MyWordsView: View {
    @Environment(WordStore.self) private var store
    @State private var deepDiveWord: Word?

    var body: some View {
        NavigationStack {
            Group {
                if store.knownWords.isEmpty {
                    ContentUnavailableView {
                        Label("No known words yet", systemImage: "checkmark.seal")
                    } description: {
                        Text("Tap “I know this” on a card in Learn and the word lands here, with its phrases and example sentence ready for a quick review before a meeting.")
                    }
                } else {
                    List {
                        Section {
                            ForEach(store.knownWords) { word in
                                KnownWordRow(word: word) {
                                    deepDiveWord = word
                                } onRelearn: {
                                    withAnimation { store.setKnown(false, for: word) }
                                }
                            }
                        } footer: {
                            Text("\(store.knownWords.count) of \(store.words.count) words known")
                                .font(Theme.monoSmall)
                        }
                    }
                    .listStyle(.insetGrouped)
                }
            }
            .background(Theme.background)
            .navigationTitle("My words")
            .settingsToolbar()
            .sheet(item: $deepDiveWord) { DeepDiveSheet(word: $0) }
        }
    }
}

/// Everything needed for a quick refresher, visible without another tap.
private struct KnownWordRow: View {
    let word: Word
    let onDeepDive: () -> Void
    let onRelearn: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text(word.word)
                    .font(Theme.serif(.title3))
                Text(word.partOfSpeech)
                    .font(Theme.monoSmall)
                    .foregroundStyle(.secondary)
                Spacer()
                HearItButton(text: word.word)
                    .scaleEffect(0.8)
            }
            Text(word.definition)
                .font(.subheadline)
            HighlightedExample(word: word, font: .subheadline)
                .foregroundStyle(.secondary)
            PhraseChips(phrases: word.goesWith)
            HStack {
                Button("Deep dive", systemImage: "text.magnifyingglass", action: onDeepDive)
                Spacer()
                Button("Relearn", systemImage: "arrow.uturn.backward", action: onRelearn)
                    .tint(.orange)
            }
            .font(.subheadline)
            // Borderless so each button gets its own tap target inside the List row.
            .buttonStyle(.borderless)
        }
        .padding(.vertical, 6)
    }
}

#Preview {
    MyWordsView()
        .environment(WordStore())
        .environment(DeepDiveService())
}
