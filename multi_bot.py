import sys
import time
import threading
from pathlib import Path

project_dir = str(Path(__file__).resolve().parent)
print("Project directory:", project_dir)
sys.path.insert(0, project_dir)

import inquirer
from rich.live import Live
import argparse
from pathlib import Path
import config
from config import load_config, Config
from config import VERSION
from api.manager import Manager
from directionalscalper.core.exchange import Exchange
from directionalscalper.core.strategies.strategy import Strategy
# Bybit rotator
from directionalscalper.core.strategies.bybit.multi.bybit_auto_rotator import BybitAutoRotator
from directionalscalper.core.strategies.bybit.multi.bybit_mfirsi_trend_rotator import BybitMFIRSITrendRotator
from directionalscalper.core.strategies.bybit.multi.bybit_mm_oneminute import BybitMMOneMinute
from directionalscalper.core.strategies.bybit.multi.bybit_mm_fiveminute import BybitMMFiveMinute
from directionalscalper.core.strategies.bybit.multi.bybit_mm_fiveminute_walls import BybitMMFiveMinuteWalls
from directionalscalper.core.strategies.bybit.multi.bybit_mm_oneminute_walls import BybitMMOneMinuteWalls
from directionalscalper.core.strategies.bybit.multi.bybit_mm_fiveminute_qfl_mfi import BybitMMFiveMinuteQFLMFI
from directionalscalper.core.strategies.bybit.multi.bybit_mm_fiveminute_qfl_mfi_autohedge import BybitMMFiveMinuteQFLMFIAutoHedge
from directionalscalper.core.strategies.bybit.multi.bybit_mm_fiveminute_qfl_mfi_eri_autohedge import BybitMMFiveMinuteQFLMFIERIAutoHedge
from directionalscalper.core.strategies.bybit.multi.bybit_mm_fiveminute_qfl_mfi_eri_autohedge_unstuck import BybitMMFiveMinuteQFLMFIERIAutoHedgeUnstuck
from directionalscalper.core.strategies.bybit.multi.bybit_qs import BybitQSStrategy
from directionalscalper.core.strategies.bybit.multi.bybit_obstrength import BybitOBStrength
from directionalscalper.core.strategies.bybit.multi.bybit_mfirsi import BybitAutoRotatorMFIRSI
from directionalscalper.core.strategies.bybit.multi.bybit_mm_playthespread import BybitMMPlayTheSpread
from directionalscalper.core.strategies.bybit.multi.bybit_obstrength_random import BybitOBStrengthRandom
from live_table_manager import LiveTableManager, shared_symbols_data


from directionalscalper.core.strategies.logger import Logger

logging = Logger(logger_name="MultiBot", filename="MultiBot.log", stream=True)

def standardize_symbol(symbol):
    return symbol.replace('/', '').split(':')[0]

def choose_strategy():
    questions = [
        inquirer.List('strategy',
                      message='Which strategy would you like to run?',
                      choices=[
                          'bybit_mm_mfirsi',
                          'bybit_mm_fivemin',
                          'bybit_mm_onemin',
                          'bybit_mfirsi_trend',
                          'bybit_obstrength',
                          'bybit_mm_fivemin_walls',
                          'bybit_mm_onemin_walls',
                          'bybit_mm_qfl_mfi',
                          'bybit_mm_qfl_mfi_autohedge',
                          'bybit_mm_qs',
                          'bybit_mm_qfl_mfi_eri_autohedge',
                          'bybit_mm_qfl_mfi_eri_autohedge_unstuck',
                      ]
                     )
    ]
    answers = inquirer.prompt(questions)
    return answers['strategy']


class DirectionalMarketMaker:
    def __init__(self, config: Config, exchange_name: str, account_name: str):
        self.config = config
        self.exchange_name = exchange_name
        self.account_name = account_name
        exchange_config = None

        for exch in config.exchanges:
            if exch.name == exchange_name and exch.account_name == account_name:  # Check both fields
                exchange_config = exch
                break

        if not exchange_config:
            raise ValueError(f"Exchange {exchange_name} with account {account_name} not found in the configuration file.")
        api_key = exchange_config.api_key
        secret_key = exchange_config.api_secret
        passphrase = exchange_config.passphrase
        self.exchange = Exchange(self.exchange_name, api_key, secret_key, passphrase)
        self.manager = Manager(
            self.exchange, 
            exchange_name=exchange_name, 
            data_source_exchange=config.api.data_source_exchange,
            api=config.api.mode, 
            path=Path("data", config.api.filename), 
            url=f"{config.api.url}{config.api.filename}"
        )

        # Fetch all possible symbols
        all_possible_symbols = self.manager.get_all_possible_symbols()

        # Initialize symbol_locks as an instance variable
        self.symbol_locks = {symbol: threading.Lock() for symbol in all_possible_symbols}


        # # Fetch all possible symbols
        # all_possible_symbols = self.manager.get_all_possible_symbols()

        # # Initialize symbol_locks
        # global symbol_locks
        # symbol_locks = {symbol: threading.Lock() for symbol in all_possible_symbols}

    def run_strategy(self, symbol, strategy_name, config, account_name, symbols_to_trade=None, rotator_symbols_standardized=None):
        symbols_allowed = None
        for exch in config.exchanges:
            if exch.name == self.exchange_name and exch.account_name == account_name:
                symbols_allowed = exch.symbols_allowed
                print(f"Matched exchange: {exchange_name}, account: {args.account_name}. Symbols allowed: {symbols_allowed}")
                break

        print(f"Multibot.py: symbols_allowed from config: {symbols_allowed}")
        
        if symbols_to_trade:
            print(f"Calling run method with symbols: {symbols_to_trade}")

        # Pass symbols_allowed and symbol_locks to the strategy constructors
        strategy = None
        if strategy_name.lower() == 'bybit_mm_mfirsi':
            strategy = BybitAutoRotatorMFIRSI(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)
        elif strategy_name.lower() == 'bybit_mm_onemin':
            strategy = BybitMMOneMinute(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)
        elif strategy_name.lower() == 'bybit_mm_fivemin':
            strategy = BybitMMFiveMinute(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)

        elif strategy_name.lower() == 'bybit_mm_fivemin_walls':
            strategy = BybitMMFiveMinuteWalls(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)
            
        elif strategy_name.lower() == 'bybit_mm_onemin_walls':
            strategy = BybitMMOneMinuteWalls(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)

        elif strategy_name.lower() == 'bybit_mm_qfl_mfi':
            strategy = BybitMMFiveMinuteQFLMFI(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)

        elif strategy_name.lower() == 'bybit_mm_qfl_mfi_autohedge':
            strategy = BybitMMFiveMinuteQFLMFIAutoHedge(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)

        elif strategy_name.lower() == 'bybit_mm_qfl_mfi_eri_autohedge':
            strategy = BybitMMFiveMinuteQFLMFIERIAutoHedge(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)
          
        elif strategy_name.lower() == 'bybit_mm_qfl_mfi_eri_autohedge_unstuck':
            strategy = BybitMMFiveMinuteQFLMFIERIAutoHedgeUnstuck(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)
           
        elif strategy_name.lower() == 'bybit_mm_qs':
            strategy = BybitQSStrategy(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)
           
        elif strategy_name.lower() == 'bybit_mfirsi_trend':
            strategy = BybitMFIRSITrendRotator(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)
           
        elif strategy_name.lower() == 'bybit_obstrength':
            strategy = BybitOBStrength(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)
           
        elif strategy_name.lower() == 'bybit_pts':
            strategy = BybitMMPlayTheSpread(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)
            
        elif strategy_name.lower() == 'bybit_obstrength_random':
            strategy = BybitOBStrengthRandom(self.exchange, self.manager, config.bot, symbols_allowed, self.symbol_locks)
           

        if strategy:
            strategy.run(symbol, rotator_symbols_standardized=rotator_symbols_standardized)

    def get_balance(self, quote, market_type=None, sub_type=None):
        if self.exchange_name == 'bitget':
            return self.exchange.get_balance_bitget(quote)
        elif self.exchange_name == 'bybit':
            #self.exchange.retry_api_call(self.exchange.get_balance_bybit, quote)
            # return self.exchange.retry_api_call(self.exchange.get_balance_bybit(quote))
            return self.exchange.get_balance_bybit(quote)
        elif self.exchange_name == 'bybit_unified':
            return self.exchange.retry_api_call(self.exchange.get_balance_bybit(quote))
        elif self.exchange_name == 'mexc':
            return self.exchange.get_balance_mexc(quote, market_type='swap')
        elif self.exchange_name == 'huobi':
            print("Huobi starting..")
        elif self.exchange_name == 'okx':
            print(f"Unsupported for now")
        elif self.exchange_name == 'binance':
            return self.exchange.get_balance_binance(quote)
        elif self.exchange_name == 'phemex':
            print(f"Unsupported for now")

    def get_open_positions(self):
        return self.exchange.get_all_open_positions_bybit()
    
    def create_order(self, symbol, order_type, side, amount, price=None):
        return self.exchange.create_order(symbol, order_type, side, amount, price)

    def get_symbols(self):
        return self.exchange.symbols


BALANCE_REFRESH_INTERVAL = 600  # in seconds

thread_to_symbol = {}
symbol_to_thread = {}
lock = threading.Lock()

def run_bot(symbol, args, manager, account_name, symbols_allowed, rotator_symbols_standardized):
    # Thread identification
    current_thread = threading.current_thread()
    thread_to_symbol[current_thread] = symbol

    # Configuration loading
    config_file_path = Path('configs/' + args.config)
    print("Loading config from:", config_file_path)
    config = load_config(config_file_path)

    # Initialize balance cache and last fetch time
    cached_balance = None
    last_balance_fetch_time = 0

    # Market maker setup
    market_maker = DirectionalMarketMaker(config, args.exchange, account_name)
    market_maker.manager = manager
    market_maker.run_strategy(symbol, args.strategy, config, account_name, symbols_to_trade=symbols_allowed, rotator_symbols_standardized=rotator_symbols_standardized)

    # Balance management
    quote = "USDT"
    current_time = time.time()
    if current_time - last_balance_fetch_time > BALANCE_REFRESH_INTERVAL or not cached_balance:
        cached_balance = market_maker.get_balance(quote)
        print(f"Futures balance: {cached_balance}")
        last_balance_fetch_time = current_time

def start_threads_for_symbols(symbols, args, manager, account_name, symbols_allowed, rotator_symbols_standardized):
    global thread_to_symbol, symbol_to_thread
    threads = []
    for symbol in symbols:
        with lock:
            if symbol not in symbol_to_thread:
                thread = threading.Thread(target=run_bot, args=(symbol, args, manager, account_name, symbols_allowed, rotator_symbols_standardized))
                thread.start()
                threads.append(thread)
                symbol_to_thread[symbol] = thread
    return threads

if __name__ == '__main__':
    # ASCII Art and Text
    sword = "====||====>"

    print("\n" + "=" * 50)
    print(f"DirectionalScalper {VERSION}".center(50))
    print("=" * 50 + "\n")

    print("Initializing", end="")
    # Loading animation
    for i in range(3):
        time.sleep(0.5)
        print(".", end="", flush=True)
    print("\n")

    # Display the ASCII art
    print("Battle-Ready Algorithm".center(50))
    print(sword.center(50) + "\n")

    parser = argparse.ArgumentParser(description='DirectionalScalper')
    parser.add_argument('--config', type=str, default='configs/config.json', help='Path to the configuration file')
    parser.add_argument('--account_name', type=str, help='The name of the account to use')
    parser.add_argument('--exchange', type=str, help='The name of the exchange to use')
    parser.add_argument('--strategy', type=str, help='The name of the strategy to use')
    parser.add_argument('--symbol', type=str, help='The trading symbol to use')
    parser.add_argument('--amount', type=str, help='The size to use')

    args = parser.parse_args()

    # Ask for exchange, strategy, and account_name if they're not provided
    if not args.exchange or not args.strategy or not args.account_name:
        questions = [
            inquirer.List('exchange',
                        message="Which exchange do you want to use?",
                        choices=['bybit', 'bitget', 'mexc', 'huobi', 'okx', 'binance', 'phemex']) if not args.exchange else None,
            inquirer.List('strategy',
                        message="Which strategy do you want to use?",
                        choices=['bybit_mm_mfirsi', 'bybit_mm_fivemin', 'bybit_mfirsi_trend',
                                'bybit_obstrength', 'bybit_mm_fivemin_walls', 'bybit_mm_onemin_walls', 'bybit_mm_qfl_mfi', 'bybit_mm_qfl_mfi_autohedge',
                                'bybit_mm_qs', 'bybit_mm_qfl_mfi_eri_autohedge', 'bybit_mm_qfl_mfi_eri_autohedge_unstuck']) if not args.strategy else None,
            inquirer.Text('account_name',
                        message="Please enter the name of the account:") if not args.account_name else None
        ]
        questions = [q for q in questions if q is not None]  # Remove None values
        answers = inquirer.prompt(questions)
        
        if not args.exchange:
            args.exchange = answers['exchange']
        if not args.strategy:
            args.strategy = answers['strategy']
        if not args.account_name:
            args.account_name = answers['account_name']

    print(f"DirectionalScalper {VERSION} Initialized Successfully!".center(50))
    print("=" * 50 + "\n")

    # Correct the path for the configuration file
    if not args.config.startswith('configs/'):
        config_file_path = Path('configs/' + args.config)
    else:
        config_file_path = Path(args.config)

    config = load_config(config_file_path)

    # config_file_path = Path('configs/' + args.config)
    # config = load_config(config_file_path)

    exchange_name = args.exchange  # Now it will have a value
    market_maker = DirectionalMarketMaker(config, exchange_name, args.account_name)

    manager = Manager(
        market_maker.exchange, 
        exchange_name=args.exchange, 
        data_source_exchange=config.api.data_source_exchange,
        api=config.api.mode, 
        path=Path("data", config.api.filename), 
        url=f"{config.api.url}{config.api.filename}"
    )

    print(f"Using exchange {config.api.data_source_exchange} for API data")

    whitelist = config.bot.whitelist
    blacklist = config.bot.blacklist
    max_usd_value = config.bot.max_usd_value

    # symbols_allowed = config.bot.symbols_allowed
  
    # Loop through the exchanges to find the correct exchange and account name
    for exch in config.exchanges:
        if exch.name == exchange_name and exch.account_name == args.account_name:
            logging.info(f"Symbols allowed changed to symbols_allowed from config")
            symbols_allowed = exch.symbols_allowed
            break
    else:
        # Default to a reasonable value if symbols_allowed is None
        logging.info(f"Symbols allowed defaulted to 10")
        symbols_allowed = 10  # You can choose an appropriate default value

    ### ILAY ###
    table_manager = LiveTableManager()
    display_thread = threading.Thread(target=table_manager.display_table)
    display_thread.daemon = True
    display_thread.start()
    ### ILAY ###

    # Fetch all symbols that meet your criteria and standardize them
    all_symbols_standardized = [standardize_symbol(symbol) for symbol in manager.get_auto_rotate_symbols(min_qty_threshold=None, whitelist=whitelist, blacklist=blacklist, max_usd_value=max_usd_value)]

    # Get symbols with open positions and standardize them
    open_position_data = market_maker.exchange.get_all_open_positions_bybit()
    open_positions_symbols = set()  # Use a set to ensure uniqueness
    for position in open_position_data:
        standardized_symbol = standardize_symbol(position['symbol'].split('/')[0])
        open_positions_symbols.add(standardized_symbol)

    open_positions_symbols = list(open_positions_symbols)  # Convert back to a list if necessary

    # # Get symbols with open positions and standardize them
    # open_position_data = market_maker.exchange.get_all_open_positions_bybit()
    # open_positions_symbols = [standardize_symbol(position['symbol']) for position in open_position_data]
    
    # print(f"Open positions symbols {open_positions_symbols}")

    # Determine new symbols to trade on
    potential_new_symbols = [symbol for symbol in all_symbols_standardized if symbol not in open_positions_symbols]
    new_symbols = potential_new_symbols[:symbols_allowed]

    # Combine open positions symbols and new symbols
    symbols_to_trade = open_positions_symbols + new_symbols

    print(f"Symbols to trade: {symbols_to_trade}")

    active_threads = start_threads_for_symbols(symbols_to_trade, args, manager, args.account_name, symbols_allowed, all_symbols_standardized)

    while True:
        with lock:
            # Refresh the set of symbols managed by currently active threads
            active_symbols = set([thread_to_symbol[t] for t in threading.enumerate() if t in thread_to_symbol])

            # Remove entries for any dead threads
            for symbol in list(symbol_to_thread.keys()):
                if not symbol_to_thread[symbol].is_alive():
                    del symbol_to_thread[symbol]

            # Fetch open positions and standardize symbol names, ensuring each symbol is unique
            open_positions = market_maker.get_open_positions()
            open_symbols = set()
            for pos in open_positions:
                symbol_name = pos['symbol'].split('/')[0]  # Assumes symbol format is like 'BTC/USDT'
                open_symbols.add(standardize_symbol(symbol_name))

            rotator_symbols_standardized = [standardize_symbol(s) for s in manager.get_auto_rotate_symbols()]

            # Start threads for new symbols not currently active or already having a thread
            new_symbols = [s for s in rotator_symbols_standardized if s not in active_symbols and s not in symbol_to_thread and s not in open_symbols]
            start_threads_for_symbols(new_symbols, args, manager, args.account_name, symbols_allowed, rotator_symbols_standardized)

            # Restart threads for symbols whose threads have terminated
            for symbol in open_symbols:
                if symbol not in active_symbols and symbol not in symbol_to_thread:
                    thread = threading.Thread(target=run_bot, args=(symbol, args, manager, args.account_name, symbols_allowed, rotator_symbols_standardized))
                    thread.start()
                    symbol_to_thread[symbol] = thread

            print(f"Active threads: {len(thread_to_symbol)}")
            time.sleep(60)
