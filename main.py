import random
from web3 import Web3
from eth_account import Account
import time
import os

# Настройки
RPC_URL = "https://ethereum-rpc.publicnode.com"
CONTRACT_ADDRESS = "0x26D85A13212433Fe6A8381969c2B0dB390a0B0ae"

# Чтение приватных ключей из файла
if not os.path.exists('pk.txt'):
    raise Exception("Файл pk.txt не найден")

with open('pk.txt', 'r') as f:
    private_keys = [line.strip() for line in f.readlines() if line.strip()]

if not private_keys:
    raise Exception("Файл pk.txt пуст или не содержит валидных ключей")

print(f"Найдено {len(private_keys)} приватных ключей")

# Минимальный ABI с только необходимыми функциями
contract_abi = [
    {
        "inputs": [],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "isMintingActive",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "hasMinted",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Подключение к блокчейну
w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    raise Exception("Не удалось подключиться к блокчейну")

# Создание объекта контракта
contract = w3.eth.contract(address = Web3.to_checksum_address(CONTRACT_ADDRESS), abi = contract_abi)

# Проверка активности минта
try:
    is_active = contract.functions.isMintingActive().call()
    print(f"Минт активен: {is_active}")

    if not is_active:
        print("Минтинг не активен в данный момент")
        exit()

except Exception as e:
    print(f"Ошибка при проверке статуса минта: {e}")
    exit()

# Обработка каждого приватного ключа
successful_mints = 0
failed_mints = 0

for i, private_key in enumerate(private_keys, 1):
    try:
        print(f"\n[{i}/{len(private_keys)}] Обработка кошелька...")

        # Получение адреса кошелька из приватного ключа
        account = Account.from_key(private_key)
        wallet_address = account.address
        print(f"Адрес кошелька: {wallet_address}")

        # Проверка, минтил ли уже этот адрес
        has_minted = contract.functions.hasMinted(wallet_address).call()
        if has_minted:
            print("⚠️  Уже минтили этот NFT")
            continue

        # Получение текущих параметров газа (EIP-1559)
        try:
            base_fee = w3.eth.get_block('latest')['baseFeePerGas']
        except:
            # Если baseFeePerGas недоступен, используем оценку
            base_fee = w3.to_wei(2, 'gwei')
        max_priority_fee_per_gas = w3.to_wei(round(random.uniform(0.101, 0.502), 2),
                                             'gwei')  # Максимальная премия майнеру
        max_fee_per_gas = base_fee + max_priority_fee_per_gas  # Максимальная общая плата за газ

        print(f"Base fee: {w3.from_wei(base_fee, 'gwei')} Gwei")
        print(f"Max fee: {w3.from_wei(max_fee_per_gas, 'gwei')} Gwei")
        print("-" * 50)

        # Получение nonce для этого кошелька
        nonce = w3.eth.get_transaction_count(wallet_address)

        # Подготовка транзакции
        transaction = contract.functions.mint().build_transaction({
            'chainId': 1,  # Ethereum Mainnet
            'gas': 200000,  # Лимит газа
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee_per_gas,
            'nonce': nonce,
        })

        # Подписание транзакции
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key = private_key)

        # Отправка транзакции
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"✅ Транзакция отправлена: https://etherscan.io/tx/0x{tx_hash.hex()}")

        # Ожидание подтверждения транзакции
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout = 300)

        if tx_receipt.status == 1:
            print(f"🎉 Минт успешно выполнен для {wallet_address}")
            successful_mints += 1
        else:
            print(f"❌ Ошибка при минте для {wallet_address}")
            failed_mints += 1

    except Exception as e:
        print(f"❌ Ошибка для кошелька {wallet_address if 'wallet_address' in locals() else 'неизвестен'}: {e}")
        failed_mints += 1

    # Небольшая пауза между транзакциями
    if i < len(private_keys):
        time.sleep(random.uniform(10, 60))

print("\n" + "=" * 50)
print("Результаты:")
print(f"Успешных минтов: {successful_mints}")
print(f"Ошибок: {failed_mints}")
print(f"Всего обработано: {len(private_keys)}")
