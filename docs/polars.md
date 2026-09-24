# Titanic Dataset

```python
dataset = "titanic"
url = f"https://raw.githubusercontent.com/mwaskom/seaborn-data/master/{dataset}.csv"

df = pl.read_csv(url)
df
```
