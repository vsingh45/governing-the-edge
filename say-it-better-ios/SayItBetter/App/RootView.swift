import SwiftUI

struct RootView: View {
    var body: some View {
        TabView {
            LearnView()
                .tabItem { Label("Learn", systemImage: "rectangle.stack") }
            QuizView()
                .tabItem { Label("Quiz", systemImage: "checklist") }
            MyWordsView()
                .tabItem { Label("My words", systemImage: "checkmark.seal") }
            AllWordsView()
                .tabItem { Label("All words", systemImage: "text.book.closed") }
        }
    }
}

#Preview {
    RootView()
        .environment(WordStore())
        .environment(DeepDiveService())
        .modelContainer(for: QuizResult.self, inMemory: true)
}
