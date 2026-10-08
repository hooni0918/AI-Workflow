public struct Wallet {
    public private(set) var balance: Int

    public init(balance: Int) {
        self.balance = balance
    }

    /// 잔액이 결제금액 이상이면 결제한다.
    public mutating func pay(_ amount: Int) -> Bool {
        if amount > 0 && balance >= amount {
            balance -= amount
            return true
        }
        return false
    }
}
