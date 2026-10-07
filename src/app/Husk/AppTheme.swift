// SPDX-License-Identifier: GPL-2.0-or-later
import SwiftUI
import UIKit

/// The app's accent colour, chosen by the user and remembered.
///
/// Light and dark are not chosen here: they are the system's, unless the user pins one in
/// Settings > Appearance (`Theme.Appearance`). This is only the colour that buttons, toggles, selected
/// states and links are tinted with. It is applied once at the root with `.tint(...)`, which SwiftUI
/// hands down to every control, so no screen has to know about it.
///
/// Rottweiler uses its own muted red accent; the original Husk target keeps indigo.
/// The preset ID and settings key remain stable to preserve existing user choices.
final class AppTheme: ObservableObject {
    static let shared = AppTheme()

    struct Preset: Identifiable {
        let id: String
        let name: String
        let color: Color
    }

    static let husk = Color(red: 0.353, green: 0.322, blue: 0.945)
    static let rottweiler = Color(red: 0.72, green: 0.25, blue: 0.24)
    static var brand: Color { ExecutionMode.noJIT ? rottweiler : husk }

    static let presets: [Preset] = [
        Preset(id: "husk", name: ExecutionMode.appName, color: brand),
        Preset(id: "blue", name: "Blue", color: .blue),
        Preset(id: "purple", name: "Purple", color: .purple),
        Preset(id: "pink", name: "Pink", color: .pink),
        Preset(id: "red", name: "Red", color: .red),
        Preset(id: "orange", name: "Orange", color: .orange),
        Preset(id: "yellow", name: "Yellow", color: .yellow),
        Preset(id: "green", name: "Green", color: .green),
        Preset(id: "teal", name: "Teal", color: .teal),
        Preset(id: "mint", name: "Mint", color: .mint),
    ]

    @Published var accentColor: Color {
        didSet { persist() }
    }

    private static let key = "husk.accentColorHex"

    private init() {
        if let hex = UserDefaults.standard.string(forKey: Self.key), let color = Color(themeHex: hex) {
            accentColor = color
        } else {
            accentColor = Self.brand
        }
    }

    func reset() { accentColor = Self.brand }

    private func persist() {
        UserDefaults.standard.set(accentColor.themeHex, forKey: Self.key)
    }
}

extension Color {
    init?(themeHex hex: String) {
        var s = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if s.hasPrefix("#") { s.removeFirst() }
        guard s.count == 6, let value = UInt32(s, radix: 16) else { return nil }
        self = Color(red: Double((value >> 16) & 0xFF) / 255,
                     green: Double((value >> 8) & 0xFF) / 255,
                     blue: Double(value & 0xFF) / 255)
    }

    var themeHex: String {
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        UIColor(self).getRed(&r, green: &g, blue: &b, alpha: &a)
        return String(format: "#%02X%02X%02X", Int((r * 255).rounded()), Int((g * 255).rounded()), Int((b * 255).rounded()))
    }

    /// Whether text on this colour should be dark.
    var isLight: Bool {
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        UIColor(self).getRed(&r, green: &g, blue: &b, alpha: &a)
        return 0.299 * r + 0.587 * g + 0.114 * b > 0.6
    }
}
