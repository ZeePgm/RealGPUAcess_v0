# Migration and compatibility

This revision promotes the accepted incremental backend adapter into the
RealGPUAcess_v0 source release. The backend base is
72e074508c462dceb7d42962c4885ecf17cc4d0d with six explicit local changes.
[Provenance](../third_party/hbf-eventlab-origin.json) and
[the complete patch](../third_party/hbf-eventlab-overlay.patch) identify them.

The GPU execution/math kernels, framework overlay, source build entries and
functional tests are copied from the accepted candidate. The release is rebuilt
in its own directory. Candidate binaries are not substituted for release builds.
Historical main-backend release files are preserved separately for rollback.

## Runtime contract changes

- TimingBackend submits Global requests to SimulationSession and the original
  HostDriver, instead of owning Device submission and command credits.
- The former child_window option is replaced by resident_fragments (minimum 64,
  default 256). This is a Host active-input fragment budget, not a GPU cache size
  or a Device command window.
- The shared asynchronous mutable model path uses the Session producer adapter.
  The unchanged synchronous immutable TensorAccessBridge is a parity reference.
- KV updates create one new identity per logical block snapshot. Producer
  dependencies preserve RAW/WAR/WAW; physical splitting/retry/replay stay in Host.
- Final Global outcomes release dependent work. Normal logical failure abandons
  unregistered input and drains registered work; severe errors/limits retain
  diagnostics and may prevent full drain.
- end_stream checks temporary drain; finish permanently closes input and checks
  final Host/Device drain. Initialization is separate from application writeback.

## Statistics and numerical invariance

peak_registered_globals replaces the old peak_children meaning. Active work is
checked with peak_resident_fragments against resident_fragments. backpressure
counts producer/Host-input deferrals rather than direct Device NotTaken events.
The compatibility field replayed_pages counts normal logical snapshot pages;
host_replay_commands records actual Host recovery commands separately.

Model logits and tokens are compared with their corresponding previous modes.
The existing native-versus-paged numerical contract is unchanged; the different
arithmetic paths are not claimed to be universally byte-identical to one another.
Modeled times, scheduler order and software wall time may differ from the old
direct-device adapter.

## Distribution

Function-based filenames remain in use. migration-map.json preserves the earlier
filename mapping; internal C/CUDA ABI symbol names remain compatible with the
pinned framework. Source packaging now preserves nested build-* source filenames,
including cmake/build-info.cmake, and excludes root build directories by location.
Machine-local model profiles and development-only plans are not distributed.

See [validation](VALIDATION.md) for fresh release checks versus inherited candidate
matrix evidence. Rebuild from a fresh source tree to regenerate location-bound
build identities.
