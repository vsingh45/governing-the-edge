import SwiftUI
import SwiftData

@main
struct SayItBetterApp: App {
    @State private var store = WordStore()
    @State private var deepDives = DeepDiveService()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .environment(deepDives)
                .task { await deepDives.checkReachability() }
        }
        .modelContainer(for: QuizResult.self)
    }
}
