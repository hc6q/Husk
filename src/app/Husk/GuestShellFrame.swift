// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation

/// A reply is complete only after both markers and the exit-status newline.
/// Decode UTF-8 after framing, so multibyte characters split by TCP survive.
enum GuestShellFrame {
    static func extract(_ bytes: Data, begin: String, end: String)
        -> (out: String, status: Int)? {
        let start = Data((begin + "\n").utf8)
        guard let first = bytes.range(of: start) else { return nil }
        let bodyStart = first.upperBound
        guard let last = bytes.range(of: Data(end.utf8),
                                     in: bodyStart..<bytes.endIndex),
              let newline = bytes[last.upperBound...].firstIndex(of: 10) else { return nil }
        let statusBytes = bytes[last.upperBound..<newline]
        guard !statusBytes.isEmpty,
              statusBytes.allSatisfy({ $0 >= 48 && $0 <= 57 }),
              let status = Int(String(decoding: statusBytes, as: UTF8.self)) else { return nil }
        return (String(decoding: bytes[bodyStart..<last.lowerBound], as: UTF8.self), status)
    }
}
