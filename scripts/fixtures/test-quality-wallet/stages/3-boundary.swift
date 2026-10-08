import Testing
@testable import Wallet

@Test func 잔액과금액동일_결제성공_잔액0() {
    var wallet = Wallet(balance: 3_000)
    let paid = wallet.pay(3_000)
    #expect(paid)
    #expect(wallet.balance == 0)
}
