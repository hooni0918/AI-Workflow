import Testing
@testable import Wallet

@Test func 잔액충분_결제성공() {
    var wallet = Wallet(balance: 10_000)
    let paid = wallet.pay(3_000)
    #expect(paid)
    #expect(wallet.balance == 7_000)
}
