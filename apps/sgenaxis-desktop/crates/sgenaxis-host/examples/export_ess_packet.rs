//! Explicit .ess capture to stdout; never publishes or modifies the source.
use sgenaxis_adapters::{ess_codec::ProductEssDecoder, StdFileSystem};
use sgenaxis_host::module_packet::export_module_packet;
use sgenaxis_spec::packet::{ExportRequest, PacketLimits};
fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 4 {
        eprintln!("usage: export_ess_packet PROJECT_ROOT RELATIVE_ESS MODULE_ID TASK_ID");
        std::process::exit(2);
    }
    let request = ExportRequest {
        relative_path: args[1].clone(),
        module_id: args[2].clone(),
        task_id: args[3].clone(),
        expected_source_sha256: None,
        limits: PacketLimits::default(),
    };
    match export_module_packet(&StdFileSystem, &ProductEssDecoder, &args[0], &request) {
        Ok(packet) => println!(
            "{}",
            serde_json::to_string_pretty(&packet).expect("packet serializable")
        ),
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1)
        }
    }
}
