import SwiftUI

struct SettingsView: View {
    @Environment(WordStore.self) private var store
    @Environment(DeepDiveService.self) private var service
    @Environment(\.dismiss) private var dismiss

    @State private var confirmingReset = false

    var body: some View {
        @Bindable var service = service

        NavigationStack {
            Form {
                Section {
                    TextField("http://your-mac.local:8765", text: $service.backendURLString)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .font(Theme.mono)
                    HStack {
                        statusLabel
                        Spacer()
                        Button("Test") {
                            Task { await service.checkReachability() }
                        }
                        .disabled(service.backendURL == nil || service.reachability == .checking)
                    }
                } header: {
                    Text("Deep dive backend")
                } footer: {
                    Text("Your personal Claude Agent SDK server (see backend/README.md). Use your Mac's .local name on home Wi-Fi, or its Tailscale name when you're away. When it can't be reached, Deep dive uses the bundled content.")
                }

                Section {
                    LabeledContent("Known words", value: "\(store.known.count) of \(store.words.count)")
                    LabeledContent("iCloud sync", value: store.isCloudSyncAvailable ? "On" : "Off (this device only)")
                    Button("Reset progress", role: .destructive) { confirmingReset = true }
                } header: {
                    Text("Progress")
                } footer: {
                    Text("Known words sync through your iCloud account. No sign-in beyond the device's own.")
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
            .confirmationDialog("Mark every word as still learning?", isPresented: $confirmingReset, titleVisibility: .visible) {
                Button("Reset progress", role: .destructive) { store.resetProgress() }
            }
            .onDisappear {
                Task { await service.checkReachability() }
            }
        }
    }

    @ViewBuilder
    private var statusLabel: some View {
        switch service.reachability {
        case .notConfigured:
            Label("Not set", systemImage: "circle.dashed").foregroundStyle(.secondary)
        case .checking:
            Label("Checking…", systemImage: "ellipsis.circle").foregroundStyle(.secondary)
        case .reachable:
            Label("Reachable", systemImage: "checkmark.circle.fill").foregroundStyle(.green)
        case .unreachable:
            Label("Can't reach it", systemImage: "exclamationmark.triangle.fill").foregroundStyle(.orange)
        }
    }
}
