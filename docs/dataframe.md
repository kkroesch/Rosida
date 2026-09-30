---

---

```python
url = "https://s3.kroesch.net/example_datasets/titanic.parquet"
df = pl.read_parquet(url).select(pl.all().name.to_lowercase())
df_clean = (
    df.select(["survived", "sex", "pclass", "age"])
    .drop_nulls(subset=["survived", "sex", "pclass"])
    .with_columns(
        # guess missing age with median
        pl.col("age").fill_null(pl.col("age").median())
    )
    .with_columns(
        pl.when(pl.col("age") <= 14).then(pl.lit("Kind"))
        .when(pl.col("age") <= 30).then(pl.lit("Junger_Erwachsener"))
        .when(pl.col("age") <= 60).then(pl.lit("Erwachsener"))
        .otherwise(pl.lit("Senior"))
        .alias("age_group"),
        pl.col("pclass").cast(pl.String)
    )
)
```

```python
survived_count = df_clean.select(pl.col('survived').sum()).item()
```

überlebende: {{survived_count}}

```python
pl.Config.set_tbl_formatting("MARKDOWN")
pl.Config.set_tbl_hide_column_data_types(True)
pl.Config.set_tbl_hide_dataframe_shape(True)

# Ab jetzt erzeugt str() direkt sauberes Markdow
```

{{str(df)}}
