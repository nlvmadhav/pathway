# ---
# title: "Automating reconciliation of messy financial transaction logs using Pathway's real-time fuzzy join"
# description: Article introducing Fuzzy Join.
# notebook_export_path: notebooks/showcases/fuzzy_join_part1.ipynb
# aside: true
# article:
#   date: '2022-10-18'
#   tags: ['tutorial', 'data-pipeline']
# keywords: ['Fuzzy join', 'reconciliation', 'unstructured', 'notebook']
# author: 'pathway'
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown] jp-MarkdownHeadingCollapsed=true
# # Automating reconciliation of messy financial transaction logs using Pathway's real-time fuzzy join
#
# ## Fuzzy joins: 'errare humanum est'
#
# As the ancient maxim says, ['errare humanum est'](https://en.wiktionary.org/w/index.php?title=errare_humanum_est): to err is human.
# More than two thousands years later, this lesson is still very accurate in our modern world.
# Everyone makes mistakes and writing does not escape this fate: the longer the text the more mistakes there will be.
# However, most mistakes we usually make are small and do not hinder understanding.
#
# Unfortunately, computers, just like accountants, don't like mistakes. Computers cannot cope with mistakes. No matter how small the mistake, the computer will just reject the whole answer and throw an error.
# You have written your 10-digit password but finished with a lower case 'a' instead of a capital 'A'? The passwords obviously do not match, and you shall enter your password again!
#
# While this zero tolerance policy may make sense for security processes, it can be terrible when users have to enter long texts.
# For example, accountants may have to enter long logs of transactions by hand, creating many opportunities for mistakes.
# If those logs have to be compared to other logs (e.g. a log automatically generated by a pay station) then mismatches would appear: 'mr' instead of 'Mr'.
# Mistakes can also come from the way the data has been collected: using nicknames instead of full names, different email addresses etc.
# While humans could be able to match those logs despite the mistakes, computers cannot.
#
# Does it mean the computer is helpless in those cases, shifting all the tedious work of matching similar but different entries to human?
# Fortunately not, several mechanisms exist to assist or even perform the matching, and **fuzzy join** is one of them: a fuzzy join is a process which automatically matches entries from different logs despite not having a perfect matching between their keys.

# %% [markdown]
# ## Fuzzy join in Pathway
#
# Fuzzy join is used to perform a join on datasets when the keys do not match exactly.
# Simple use cases include matching lower case strings with camelCase strings or matching
# floats with some precision threshold.
#
# Pathway's standard library comes with a powerful `smart_fuzzy_join` functionality.
# This tutorial is a showcase of its capabilities. We will develop a Data Application which allows for fuzzy-joining
# two streams of data against each other, and also for maintaining audit entries and updating results on the fly. Here is a sneak preview:
#
# ![Demo animation](https://pathway.com/assets/content/showcases/fuzzy_join/demo.gif)
#
# ## The data
#
# We will be doing the fuzzy-join between two datasets on money transfers’ banking logs.
# When doing banking or bookkeeping, this operation would be known as [reconciliation](https://en.wikipedia.org/w/index.php?title=Reconciliation_(accounting)&oldid=1100237463) of
# two sets of transactions records.
# One dataset comes in a perfectly organized format - csv, the other dataset consists of
# 'human written' lines describing the transactions.
#
#
# Here are samples from the datasets:
#
#  **Data sourced automatically from a bank feed, in 'standard' CSV format**
#
# |id    |date      |amount|recipient |sender        |recipient_acc_no            |sender_acc_no               |
# |------|----------|------|----------|--------------|----------------------------|----------------------------|
# |0     |2020-06-04|8946  |M. Perez  |Jessie Roberts|HU30186000000000000008280573|ES2314520000000006226902    |
# |1     |2014-08-06|8529  |C. Barnard|Mario Miller  |ES8300590000000002968016    |PL59879710390000000009681693|
# |2     |2017-01-22|5048  |S. Card   |James Paletta |PL65889200090000000009197250|PL46193013890000000009427616|
# |3     |2020-09-15|7541  |C. Baxter |Hector Haley  |PL40881800090000000005784046|DE84733500000003419377      |
# |4     |2019-05-25|3580  |L. Prouse |Ronald Adams  |PL44124061590000000008986827|SI54028570008259759         |
#
#
# The first dataset is sourced automatically from a bank feed. Every few seconds a new batch of transactions is saved to `transactions/formatA/batch_timestamp.csv`.
#
#  **Transaction logs entered by hand**
#
# |id |description|
# |---|-----------|
# |0  |Received 8521 €  on 2014-08-07 by INTERNATIONAL interest payment from ??? to C. Barnard, recipient acc. no. 000002968016 by BANCO DE MADRID, amount EUR €, flat fee 8 € |
# |1  |EUR 8944 on 2020-06-06 by INTERNATIONAL transfer credited to 00000000008280573 (M. Perez) by BNP Paribas Securities Services,  fee EUR 2, amount EUR 8946. |
# |2  |Finally got 5M quid on 2017-01-23 by DOMESTIC payment from Sergio Marquina to Bella Ciao, r. acc. 0000000009197250, oryg. amount 5_000_048, fees 5 quid. |
# |3  |3578 EUR am 2019-05-25 von INTERNATIONAL dividend payment by Pathway Inc. an L. Prouse, Empfängerkonto 8986827, Betrag 3580 EUR |
# |4  |Received 7540 EUR on 2020-09-15. Invoice, recipient C. Baxter, 0000000005784046, amount EUR 7541, fees EUR 1 |
#
#
# As you can see, it seems that each entry in the first dataset (data sourced automatically) has a corresponding entry in the other dataset (transaction logs entered by hand).
# In this example we will use the `smart_fuzzy_join` function from Pathway's standard library to make sure all is correctly matched.
#
# ## What are we going to obtain?
# We want to obtain a table in which the matchings are expressed, e.g. the entry 0 for the first table corresponds to the entry 1 in the second table.
# In addition, we will include the confidence, a number expressing how confident we are in the matching.
#
# ## Code
# First things first - imports:

# %%
import pandas as pd

import pathway as pw

# %% [markdown]
# And now, here come a few lines of code that read two datasets, try to match rows, and report matchings by writing to a csv file.
#
#
# The data is read from csv files.
# For the purpose of this demonstration we will simply print a table with matchings found on the data sample presented above.
# But the code below works also in a production environment. In production:
# - All csv files will be dynamically ingested from these directories in their order of appearance.
# - The output will be updated immediately as new data appears at input.

# %%
# Uncomment to download the required files.
# # %%capture --no-display
# # !wget https://public-pathway-releases.s3.eu-central-1.amazonaws.com/data/fuzzy_join_part_1_transactionsA.csv -O transactionsA.csv
# # !wget https://public-pathway-releases.s3.eu-central-1.amazonaws.com/data/fuzzy_join_part_1_transactionsB.csv -O transactionsB.csv

# %% [markdown]
# We use [our csv connectors](/developers/user-guide/connect/connectors/csv_connectors/) to read the csv files:


# %%
class TransactionsA(pw.Schema):
    recipient_acc_no: str = pw.column_definition(primary_key=True)
    date: str
    amount: str
    recipient: str
    sender: str
    sender: str
    sender_acc_no: str


class TransactionsB(pw.Schema):
    description: str = pw.column_definition(primary_key=True)


transactionsA = pw.io.csv.read(
    "./transactionsA.csv",
    schema=TransactionsA,
    mode="static",
)
transactionsB = pw.io.csv.read(
    "./transactionsB.csv",
    schema=TransactionsB,
    mode="static",
)
pw.debug.compute_and_print(transactionsA)
pw.debug.compute_and_print(transactionsB)


# %% [markdown]
# Then we use our fuzzy join functions to do the reconciliation between the two tables.


# %%
def match_transactions(transactionsA, transactionsB):
    matching = pw.ml.smart_table_ops.fuzzy_match_tables(transactionsA, transactionsB)
    transactionsA_reconciled = (
        pw.Table.empty(left=pw.Pointer, right=pw.Pointer, confidence=float)
        .update_rows(transactionsA.select(left=None, right=None, confidence=0.0))
        .update_rows(
            matching.select(
                pw.this.left, pw.this.right, confidence=pw.this.weight
            ).with_id(pw.this.left)
        )
    )
    return transactionsA_reconciled


pw.debug.compute_and_print(match_transactions(transactionsA, transactionsB))
# %% [markdown]
# Success, all matchings were found!
#
# Super easy, few lines of code and you flawlessly manage datasets in different formats.
# Hassle-free.
#
# ## Scaling with Pathway
#
# `smart_fuzzy_join` is able to handle much bigger datasets.
# Feel free to test it on your own data or use the full datasets from this tutorial,
# available [in this Google Spreadsheet](https://docs.google.com/spreadsheets/d/1cXAPcmkq0t0ieIQCBrdKPG2Fq_DimAzzxfHsDWrtdW0/edit?usp=sharing).
#
# <!-- It took TODO seconds to run the `match_formats` on the full datasets TODO rows each. -->
#
# In the tutorial we just printed a matching found on a small data sample. In a dynamic production environment:
# - All csv files will be dynamically ingested from these directories in order of appearance.
# - **The output will be updated immediately as new data appears at input.**
#
# ## Conclusion and follow-up tasks
#
# While errors are human and we are unlikely to stop making some, we can free ourselves of the pain of correcting them each time something goes wrong.
# Sometimes, entries are harder to match and may require help: in that case you can check out our [extension](/developers/templates/etl/fuzzy_join_chapter2) and see how we extend our pipeline with an auditor that supervises the process of reconciliation.
# From now on, you have no excuses for having mismatching logs: 'errare humanum est, perseverare diabolicum'!
#
#
# If you would like to get some more experience with Pathway, you can try those two challenges:
#
# **Challenge 1**
#
# Extend the `match_transactions` function so that, after finding a matching, it extends the first input table (standard csv format) with columns 'fees' and 'currency'.
#
# **Challenge 2**
#
# Try to augment the datasets so that they are still reasonable but `smart_fuzzy_join` fails to find all matchings 😉
