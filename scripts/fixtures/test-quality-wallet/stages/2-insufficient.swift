import Testing
@testable import Wallet

@Test func 잔액부족_결제거절_잔액유지() {
    var wallet = Wallet(balance: 2_000)
    let paid = wallet.pay(3_000)
    #expect(!paid)
    #expect(wallet.balance == 2_000)
}
