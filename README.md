# Irish Lotto Predictor

A Python tool that scrapes recent Irish Lotto results and generates predictions based on hot/cold number analysis.

## 📋 Overview

This tool collects Irish Lotto (main draw) results from lottery.ie and provides statistical analysis to identify frequently drawn and rarely drawn numbers. It offers multiple prediction strategies for entertainment purposes.

### ⚠️ Important Disclaimer

**Irish Lotto draws are independent random events.** The numbers drawn have no influence on future draws. This tool is for entertainment only and cannot improve your odds of winning. Play responsibly.

## 🚀 Usage

```bash
python irish_lotto.py scrape                # Fetch latest results and save locally
python irish_lotto.py stats                 # Show frequency breakdown
python irish_lotto.py predict               # Suggest 6 numbers from hot numbers
python irish_lotto.py predict --cold        # Suggest 6 numbers from cold numbers
python irish_lotto.py predict --weighted    # Suggest 6 numbers using frequency-weighted random pick
python irish_lotto.py list                  # Show all draws currently stored
```

## 📁 Data Storage

Results are stored in `lotto_results.json` in the project directory. Running `scrape` accumulates history over time, allowing you to build a dataset for analysis.

## 🔧 Requirements

- Python 3.7+
- Internet connection (for scraping)

## 📦 Installation

```bash
git clone https://github.com/mrbacco/new_predictor.git
cd new_predictor
python irish_lotto.py scrape
python irish_lotto.py predict
```

## 📝 License

MIT License - See LICENSE file for details

## 👤 Author

mrbacco04@gmail.com (August 2026)