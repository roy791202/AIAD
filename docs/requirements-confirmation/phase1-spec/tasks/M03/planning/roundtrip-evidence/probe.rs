use std::{env,fs};
fn main() { let a:Vec<String>=env::args().collect(); let input=fs::read_to_string(&a[1]).unwrap(); match sgenaxis_host::parse_design_json(&input) { Ok(doc)=>match sgenaxis_host::serialize_design(&doc) {Ok(out)=>{fs::write(&a[2],out).unwrap();println!("ACCEPTED");},Err(e)=>println!("REJECTED_SERIALIZE: {e}")},Err(e)=>println!("REJECTED_PARSE: {e}")}}
