import SwiftUI

/// The example sentence with the `[target]` span emphasised in the accent colour.
struct HighlightedExample: View {
    let word: Word
    var font: Font = .body

    var body: some View {
        Text(attributed)
            .font(font)
            .fixedSize(horizontal: false, vertical: true)
    }

    private var attributed: AttributedString {
        word.exampleSegments.reduce(into: AttributedString()) { result, segment in
            var piece = AttributedString(segment.text)
            if segment.emphasised {
                piece.inlinePresentationIntent = .stronglyEmphasized
                piece[AttributeScopes.SwiftUIAttributes.ForegroundColorAttribute.self] = Color.accentColor
                piece[AttributeScopes.SwiftUIAttributes.BackgroundColorAttribute.self] = Color.accentColor.opacity(0.12)
            }
            result += piece
        }
    }
}

/// "Instead of saying '…', say *word*."
struct InsteadOfSwap: View {
    let word: Word

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "arrow.triangle.swap")
                .foregroundStyle(Color.accentColor)
            (Text("Instead of saying ")
                + Text("“\(word.insteadOf)”").italic()
                + Text(", say ")
                + Text(word.word).bold().foregroundColor(.accentColor)
                + Text("."))
                .font(.subheadline)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

/// Speaker button that reads the word aloud.
struct HearItButton: View {
    let text: String

    var body: some View {
        Button {
            Speaker.shared.speak(text)
        } label: {
            Image(systemName: "speaker.wave.2.fill")
                .font(.title3)
                .frame(width: 44, height: 44)
                .background(Color.accentColor.opacity(0.1), in: Circle())
        }
        .buttonStyle(.borderless)
        .accessibilityLabel("Hear \(text)")
    }
}

/// Category · part of speech, in mono.
struct WordMeta: View {
    let word: Word

    var body: some View {
        Text("\(word.category.uppercased()) · \(word.partOfSpeech)")
            .font(Theme.monoSmall)
            .foregroundStyle(.secondary)
    }
}

/// Horizontally scrolling filter chips shared by Learn, Quiz and All words.
struct CategoryChips: View {
    @Environment(WordStore.self) private var store

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                chip("All", value: nil)
                ForEach(store.categories, id: \.self) { category in
                    chip(category, value: category)
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 6)
        }
    }

    private func chip(_ title: String, value: String?) -> some View {
        let selected = store.categoryFilter == value
        return Button {
            store.categoryFilter = value
        } label: {
            Text(title)
                .font(Theme.mono)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .foregroundStyle(selected ? Color.white : Color.primary)
                .background(
                    Capsule().fill(selected ? Color.accentColor : Theme.surface)
                )
                .overlay(Capsule().strokeBorder(selected ? Color.clear : Theme.hairline, lineWidth: 0.5))
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}

/// Toolbar gear that opens Settings; added to every tab.
struct SettingsToolbar: ViewModifier {
    @State private var showingSettings = false

    func body(content: Content) -> some View {
        content
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showingSettings = true
                    } label: {
                        Image(systemName: "gearshape")
                    }
                    .accessibilityLabel("Settings")
                }
            }
            .sheet(isPresented: $showingSettings) {
                SettingsView()
            }
    }
}

extension View {
    func settingsToolbar() -> some View { modifier(SettingsToolbar()) }
}
