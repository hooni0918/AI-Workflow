public struct Wallet {
    public private(set) var balance: Int

    public init(balance: Int) {
        self.balance = balance
    }
}
