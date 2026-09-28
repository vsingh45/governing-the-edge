import Foundation

/// Persists the "known words" set in `UserDefaults` for instant local reads and mirrors it to
/// iCloud Key-Value Store so it follows the user across their own devices. When iCloud isn't
/// available (signed out, or the entitlement is missing) it silently stays local-only.
final class KnownWordsSync {
    private static let key = "knownWords"

    private let defaults: UserDefaults
    private let cloud = NSUbiquitousKeyValueStore.default
    private var observer: NSObjectProtocol?

    /// Called on the main queue when another device changed the set.
    var onRemoteChange: ((Set<String>) -> Void)?

    var isCloudAvailable: Bool {
        FileManager.default.ubiquityIdentityToken != nil
    }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        guard isCloudAvailable else { return }
        observer = NotificationCenter.default.addObserver(
            forName: NSUbiquitousKeyValueStore.didChangeExternallyNotification,
            object: cloud,
            queue: .main
        ) { [weak self] note in
            self?.handleExternalChange(note)
        }
        cloud.synchronize()
    }

    deinit {
        if let observer { NotificationCenter.default.removeObserver(observer) }
    }

    func load() -> Set<String> {
        var known = Set(defaults.stringArray(forKey: Self.key) ?? [])
        if isCloudAvailable, let remote = cloud.array(forKey: Self.key) as? [String] {
            known.formUnion(remote)
        }
        return known
    }

    func save(_ known: Set<String>) {
        let sorted = known.sorted()
        defaults.set(sorted, forKey: Self.key)
        guard isCloudAvailable else { return }
        cloud.set(sorted, forKey: Self.key)
        cloud.synchronize()
    }

    private func handleExternalChange(_ note: Notification) {
        guard
            let changedKeys = note.userInfo?[NSUbiquitousKeyValueStoreChangedKeysKey] as? [String],
            changedKeys.contains(Self.key)
        else { return }

        let remote = Set(cloud.array(forKey: Self.key) as? [String] ?? [])
        let reason = note.userInfo?[NSUbiquitousKeyValueStoreChangeReasonKey] as? Int
        let merged: Set<String>
        if reason == NSUbiquitousKeyValueStoreInitialSyncChange {
            // First sync on this device: keep anything learned offline before iCloud caught up.
            merged = remote.union(defaults.stringArray(forKey: Self.key) ?? [])
            save(merged)
        } else {
            // A newer write from another device wins, so "Relearn" propagates too.
            merged = remote
            defaults.set(merged.sorted(), forKey: Self.key)
        }
        onRemoteChange?(merged)
    }
}
