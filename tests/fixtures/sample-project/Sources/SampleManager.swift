// Synthetic Swift fixture for Surface 4 (code comments).
// The TODO/FIXME/HACK lines below are intentional fixture content.

import Foundation

final class SampleManager {

    func loadData() {
        // TODO: handle the missing-cache case before shipping
        let cache: [String] = []
        _ = cache
    }

    func saveData() {
        // FIXME: add retry on transient failures
    }

    func purgeData() {
        // HACK: temporary workaround until the proper API exists
    }

    func migrateData() {
        // MIGRATION-NOTE: bump schema version to v3 once tests pass
    }
}
