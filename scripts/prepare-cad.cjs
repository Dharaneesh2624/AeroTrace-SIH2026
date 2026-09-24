// Restore generated local CAD files from the repository's compressed assets.
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
const root=path.resolve(__dirname,'..');
function restore(source,target){const output=path.join(root,target);if(fs.existsSync(output)){console.log('Already present: '+target);return;}fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,zlib.gunzipSync(fs.readFileSync(path.join(root,source))),{flag:'wx'});console.log('Restored: '+target);}
restore('public-demo/public/engine.glb.gz','desktop/public/engine.glb');
if(process.argv.includes('--step'))restore('cad/models/AE300_R4_Assembly.step.gz','cad/models/AE300_R4_Assembly.step');
