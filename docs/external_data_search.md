# External QoT dataset search

Search date: 2026-11-23. No Kaggle API credential was configured, and no external dataset was downloaded. The core labels will still be generated with the pinned GNPy simulator.

## Candidate sources

### Fraunhofer HHI QoT Dataset Collection — strongest future validation candidate

The collection contains four optical-network QoT datasets, each with over 1.2 million samples. They include OSNR, SNR, BER, and a binary BER-threshold feasibility label. The published description says the datasets were generated with Fraunhofer HHI's PLATON/network simulation and a nonlinear channel model, so they are **simulated**, not field measurements. The dataset collection page points to a download portal requiring a form, email delivery, and acceptance of CC BY 4.0 terms. This could be useful for a clearly separated cross-simulator comparison, but it should not be mixed with GNPy training labels because the schemas, topologies, and simulator assumptions differ. Download is deferred until access and terms are reviewed by the project owner.

Sources: [HHI QoT Dataset Collection](https://www.hhi.fraunhofer.de/en/pn-software/qot-dataset-collection.html); [HHI download portal](https://networkdata.hhi.fraunhofer.de/); [portal license agreement](https://creativecommons.org/licenses/by/4.0/legalcode).

### Kaggle Optical Network Transmission Dataset — not suitable for core QoT estimation

The page reports 4,000 rows and 22 columns with a categorical `Transmission_Quality` target (`High`, `Medium`, `Low`). Its feature list mixes optical/network terms with atmospheric turbulence, visibility, humidity, and weather. The page labels it CC0, but its data provenance and relationship to coherent long-haul fiber QoT are not established from the available description. It is therefore not suitable as a labeled QoT benchmark for this project. No download was made.

Source: [Kaggle Optical Network Transmission Dataset](https://www.kaggle.com/datasets/zara2099/optical-network-transmission-dataset).

### Optical network soft failure dataset — possible separate monitoring use

The Mendeley page describes 756 lightpaths and 900 training / 300 test time samples per lightpath. It includes length, ECL current, received power, OSNR, and BER, with no-failure and ECL-, EDFA-, and NLI-related soft-failure labels. The page reports CC BY 4.0. This is closer to optical monitoring/soft-failure classification than to the project's route-level GNPy GSNR regression target, so it is not selected for the core model. It could be reconsidered for a separate monitoring extension after inspection of the files and paper.

Source: [Optical network soft failure dataset, Mendeley Data](https://data.mendeley.com/datasets/y3pspy7j83/1), DOI [10.17632/y3pspy7j83.1](https://doi.org/10.17632/y3pspy7j83.1).

### Large-Scale Synthetic Dataset for Q-Factor Prediction — not selected

The page reports one million synthetic samples with OSNR, launch power, fiber length, chromatic dispersion, and nonlinear effects as inputs. Its Q-factor target is explicitly modeled with a hand-crafted nonlinear combination of input features plus added Gaussian noise. Although the page reports CC BY 4.0, it is not a physical simulator output or independent field dataset and does not represent network topology/lightpaths. It is not selected for training or validation.

Source: [Large-Scale Synthetic Dataset for Q-Factor Prediction, Mendeley Data](https://data.mendeley.com/datasets/6fcnwdjxt5), DOI [10.17632/6fcnwdjxt5.1](https://doi.org/10.17632/6fcnwdjxt5.1).

## Decision

Do not download any candidate at Phase 0. GNPy-generated labels remain the primary source of truth. The HHI collection is the best candidate for optional, explicitly external cross-simulator evaluation, but access requires submitting the owner's name, email, affiliation, and agreement to the stated license/privacy terms. No personal information has been submitted. The other sources are either mismatched to the core task or synthetic in a way that adds little independent validation value.
