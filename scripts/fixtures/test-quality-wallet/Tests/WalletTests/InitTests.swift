import Testing
@testable import Wallet

@Test func initKeepsBalance() {
    #expect(Wallet(balance: 5).balance == 5)
}
