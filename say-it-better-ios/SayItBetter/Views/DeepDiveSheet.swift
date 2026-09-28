import SwiftUI

struct DeepDiveSheet: View {
    let word: Word

    @Environment(DeepDiveService.self) private var service
    @Environment(\.dismiss) private var dismiss

    @State private var content: DeepDive?
    @State private var source: DeepDiveService.Source?
    @State private var loading = true

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    header
                    if loading {
                        HStack(spacing: 10) {
                            ProgressView()
                            Text(content == nil ? "Loading…" : "Checking your backend for a live version…")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                    }
                    if let content {
                        DeepDiveContent(content: content)
                    } else if !loading {
                        Text("No deep dive is available for this word yet. Start your backend (see Settings) to generate one live.")
                            .foregroundStyle(.secondary)
                            .card()
                    }
                    SentenceCoach(word: word)
                    references
                }
                .padding()
            }
            .background(Theme.background)
            .navigationTitle("Deep dive")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .task(id: word.word) { await load() }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                Text(word.word)
                    .font(Theme.headword)
                    .minimumScaleFactor(0.6)
                Spacer()
                HearItButton(text: word.word)
            }
            Text("\(content?.pronunciation.nonEmpty ?? word.pronunciation) · \(content?.partOfSpeech.nonEmpty ?? word.partOfSpeech)")
                .font(Theme.mono)
                .foregroundStyle(.secondary)
            if let source {
                Label(source == .live ? "Live from your backend" : "Offline · bundled content",
                      systemImage: source == .live ? "bolt.horizontal.circle" : "internaldrive")
                    .font(Theme.monoSmall)
                    .foregroundStyle(source == .live ? Color.accentColor : .secondary)
            }
        }
    }

    private var references: some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionLabel("References")
            ForEach(ReferenceLinks.links(for: word.word)) { link in
                Link(destination: link.url) {
                    HStack {
                        Text(link.title)
                        Spacer()
                        Image(systemName: "arrow.up.right.square")
                    }
                }
            }
        }
        .card()
    }

    private func load() async {
        // Show bundled content immediately, then upgrade to live content if the backend answers.
        if let bundled = service.bundledDeepDive(for: word.word) {
            content = bundled
            source = .bundled
            loading = service.backendURL != nil
        }
        let result = await service.deepDive(for: word.word)
        if let result {
            content = result.0
            source = result.1
        }
        loading = false
    }
}

private struct DeepDiveContent: View {
    let content: DeepDive

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            section("Meaning") { Text(content.meaning) }

            if !content.origin.isEmpty {
                section("Word origin") { Text(content.origin) }
            }

            if !content.family.isEmpty {
                section("Word family") {
                    ForEach(content.family, id: \.self) { member in
                        (Text(member.word).font(Theme.serif(.body)) + Text("  \(member.meaning)").foregroundColor(.secondary))
                    }
                }
            }

            if !content.collocations.isEmpty {
                section("Collocations") { PhraseChips(phrases: content.collocations) }
            }

            if !content.compare.isEmpty {
                section("Compared with") {
                    ForEach(content.compare, id: \.self) { item in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(item.word).font(Theme.serif(.body))
                            Text(item.difference).foregroundStyle(.secondary)
                        }
                    }
                }
            }

            if !content.mistake.isEmpty {
                section("Common mistake") {
                    Label {
                        Text(content.mistake)
                    } icon: {
                        Image(systemName: "exclamationmark.triangle").foregroundStyle(.orange)
                    }
                }
            }

            if !content.examples.isEmpty {
                section("At work") {
                    ForEach(content.examples, id: \.self) { example in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(example.setting.uppercased())
                                .font(Theme.monoSmall)
                                .foregroundStyle(Color.accentColor)
                            Text(example.sentence)
                        }
                    }
                }
            }

            if !content.tip.isEmpty {
                section("Memory tip") {
                    Label {
                        Text(content.tip)
                    } icon: {
                        Image(systemName: "lightbulb").foregroundStyle(.yellow)
                    }
                }
            }
        }
    }

    private func section<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionLabel(title)
            content()
        }
        .fixedSize(horizontal: false, vertical: true)
        .card()
    }
}

/// "Write your own sentence, get feedback." Needs the live backend; offline it only checks
/// that the word was actually used.
private struct SentenceCoach: View {
    let word: Word

    @Environment(DeepDiveService.self) private var service
    @State private var sentence = ""
    @State private var feedback: SentenceFeedback?
    @State private var errorMessage: String?
    @State private var checking = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            SectionLabel("Try it yourself")
            TextField("Write a sentence using “\(word.word)”", text: $sentence, axis: .vertical)
                .lineLimit(2...5)
                .textFieldStyle(.roundedBorder)

            Button {
                Task { await check() }
            } label: {
                if checking {
                    ProgressView()
                } else {
                    Text("Get feedback")
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(sentence.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || checking)

            if let feedback {
                VStack(alignment: .leading, spacing: 6) {
                    Label(verdictTitle(feedback.verdict), systemImage: verdictIcon(feedback.verdict))
                        .font(.headline)
                        .foregroundStyle(verdictColor(feedback.verdict))
                    Text(feedback.feedback)
                    if let improved = feedback.improved, !improved.isEmpty {
                        Text("Try: \(improved)")
                            .italic()
                            .foregroundStyle(.secondary)
                    }
                }
            }
            if let errorMessage {
                Text(errorMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .card()
    }

    private func check() async {
        let text = sentence.trimmingCharacters(in: .whitespacesAndNewlines)
        checking = true
        feedback = nil
        errorMessage = nil
        defer { checking = false }

        do {
            feedback = try await service.checkSentence(text, word: word.word)
        } catch {
            // Offline fallback: the one check we can do honestly without a model.
            if word.isUsed(in: text) {
                errorMessage = "You used “\(word.word)”. Detailed feedback needs your backend: \(error.localizedDescription)"
            } else {
                errorMessage = "“\(word.word)” doesn't appear in your sentence yet. (Detailed feedback needs your backend.)"
            }
        }
    }

    private func verdictTitle(_ verdict: String) -> String {
        switch verdict {
        case "good": return "Sounds natural"
        case "almost": return "Nearly there"
        default: return "Not quite"
        }
    }

    private func verdictIcon(_ verdict: String) -> String {
        switch verdict {
        case "good": return "checkmark.circle.fill"
        case "almost": return "exclamationmark.circle.fill"
        default: return "xmark.circle.fill"
        }
    }

    private func verdictColor(_ verdict: String) -> Color {
        switch verdict {
        case "good": return .green
        case "almost": return .orange
        default: return .red
        }
    }
}

private extension String {
    var nonEmpty: String? { isEmpty ? nil : self }
}

#Preview {
    DeepDiveSheet(word: WordLoader.load()[0])
        .environment(DeepDiveService())
}
