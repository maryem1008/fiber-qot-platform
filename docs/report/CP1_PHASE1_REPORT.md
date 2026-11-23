# CP1 - Phase 1 topology and GNPy checkpoint

## Status

Phase 1 implementation is complete for topology conversion and GNPy compatibility. The mandatory CP1 approval
is required before Phase 2 begins.

## Selected accepted topologies

### Internet Topology Zoo

| Topology | Nodes | Links | Complete coordinates |
|---|---:|---:|---|
| Aarnet | 19 | 24 | Yes |
| AttMpls | 25 | 56 | Yes |
| Bics | 33 | 48 | Yes |
| CrlNetworkServices | 33 | 38 | Yes |
| Bellcanada | 48 | 64 | Yes |
| Darkstrand | 28 | 31 | Yes |
| EliBackbone | 20 | 30 | Yes |
| Goodnet | 17 | 31 | Yes |
| Agis | 25 | 30 | Yes |
| Palmetto | 45 | 64 | Yes |
| Spiralight | 15 | 16 | Yes |
| Geant2009 | 34 | 52 | Yes |
| Bbnplanet | 27 | 28 | Yes |
| Sago | 18 | 17 | Yes |

### SNDlib

| Topology | Nodes | Links | Complete coordinates |
|---|---:|---:|---|
| Germany50 | 50 | 88 | Yes |
| Nobel-Germany | 17 | 26 | Yes |
| India35 | 35 | 80 | Yes |

### Illustrative synthetic network

Tunisia is a 12-city ring-plus-mesh demonstration with 14 links and complete coordinates. It is explicitly
synthetic and illustrative; it is not a claim of an existing Tunisian operator network.

## GNPy evidence

GNPy 3.0.1 loaded all accepted converted networks without structural load failures. The generated Tunisia
network was also executed end to end from `trx_Bizerte` to `trx_Sfax`.

The example path was 407 km and contained 7 fiber spans. GNPy returned:

- Final GSNR in 0.1 nm: 21.15 dB
- Final GSNR in signal bandwidth: 17.07 dB
- OSNR ASE in 0.1 nm: 21.65 dB
- OSNR ASE in signal bandwidth: 17.57 dB

These are GNPy simulation outputs, not measured network results.

## Transceiver modes and OSNR thresholds

The values below come directly from GNPy's installed `eqpt_config.json`:

- `vendorA_trx-type1`: mode 1 = 11 dB OSNR; mode 2 = 15 dB OSNR.
- `Voyager`: mode 1 = 12 dB; mode 3 = 18 dB; mode 2 = 21 dB; mode 4 = 16 dB OSNR.

Feasibility will use the exact selected mode and reference-bandwidth convention in later phases. No guessed
GSNR threshold was added to the configuration.

## Problems and assumptions

- Several candidate Zoo GraphML files were rejected because node coordinates were missing.
- Fourteen-node and seven-node candidates were outside the preferred 15-60-node Zoo range.
- GNPy emits a non-fatal warning that the equipment Roadm entry omits `type_variety` and uses `default`.
- GNPy emitted amplifier-gain warnings on short Tunisia links because fixed medium-gain amplifiers were used
  for spans below the amplifier minimum gain. This is recorded for Phase 2 model and physical configuration review.
- Zoo and SNDlib mirror sources require their license and provenance statements to be retained carefully.

## Verification

- `make phase1` completes conversion.
- `make phase1-smoke` loads converted GNPy networks.
- Three pytest tests pass.
- Ruff lint passes.

## Next step

Stop here. Reply `go` to begin Phase 2 dataset generation.
