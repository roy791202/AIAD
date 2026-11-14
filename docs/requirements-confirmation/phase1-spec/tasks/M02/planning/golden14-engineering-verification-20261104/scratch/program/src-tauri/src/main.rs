mod domain;
mod ports;

fn main() {
    // Shell only: no generated business command or persistence implementation.
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("candidate shell startup failed");
}
