import Testing
@testable import Wallet

@Test func 영원결제_거절() {
    var wallet = Wallet(balance: 3_000)
    let paid = wallet.pay(0)
    #expect(!paid)
    #expect(wallet.balance == 3_000)
}
