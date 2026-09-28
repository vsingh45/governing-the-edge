import SwiftUI

/// A work tool, not a toy: calm grouped backgrounds, one blue accent (AccentColor), a serif
/// display face for headwords, the system sans for body text and SF Mono for labels.
enum Theme {
    static let background = Color(uiColor: .systemGroupedBackground)
    static let surface = Color(uiColor: .secondarySystemGroupedBackground)
    static let hairline = Color(uiColor: .separator)

    static func serif(_ style: Font.TextStyle, weight: Font.Weight = .semibold) -> Font {
        .system(style, design: .serif).weight(weight)
    }

    static let headword = serif(.largeTitle)
    static let mono = Font.system(.footnote, design: .monospaced)
    static let monoSmall = Font.system(.caption, design: .monospaced)
}

/// Uppercase mono section label, e.g. "GOES WITH".
struct SectionLabel: View {
    let text: String

    init(_ text: String) { self.text = text }

    var body: some View {
        Text(text.uppercased())
            .font(Theme.monoSmall)
            .tracking(0.8)
            .foregroundStyle(.secondary)
    }
}

/// A rounded card surface used throughout the app.
struct CardBackground: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.surface, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

extension View {
    func card() -> some View { modifier(CardBackground()) }
}
