// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "Wallet",
    products: [.library(name: "Wallet", targets: ["Wallet"])],
    targets: [
        .target(name: "Wallet"),
        .testTarget(name: "WalletTests", dependencies: ["Wallet"]),
    ]
)
