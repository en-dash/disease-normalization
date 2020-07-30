# `tzlink`: Biomedical Entity Normalisation

## Instructions

1. Clone the repo.
1. Change into the repo directory and run `make init` (or just `make`) to download the datasets.
1. Optionally run `make optional` to obtain additional data resources (eg. for subword-units). Requires authentication.
1. Run `make run` to run an experiment with default settings.


## Dependencies

### Required
* `keras`
* `gensim`
* `numpy` (implied by the previous anyway)

### Optional
* `subword-nmt`
