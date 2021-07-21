# Dataiku DSS Plugin Library

This repo contains reusable code to help develop Dataiku DSS plugins.

## Included libs

- [dku_config](dkulib/dku_config) (Last update: 2021-07): Gives the ability to check form parameters in the backend and display understandable messages if it
 fails.
- [nlp](dkulib/nlp) (Last update: 2021-01): Detects languages, tokenize, correct misspellings and clean text data.
- [io_utils](dkulib/io_utils) (Last update: 2021-01): Input / output utility functions which do not need the Dataiku API.
- [dku_io_utils](dkulib/dku_io_utils) (Last update: 2021-07): Input / output utility functions to read/write from and to Dataiku objects e.g., chunked read/transform/write of dataiku Datasets.
- [parallelizer](dkulib/parallelizer) (Last update: 2021-07): Applies a function to a pandas DataFrame with parallelization, error logging and progress tracking.

## License

This library is distributed under the [Apache License version 2.0](LICENSE).
