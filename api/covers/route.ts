import {env} from '../../runtime.ts';
import {isAdmin,json,sameOrigin} from '../../lib/cms.ts';
export async function POST(request:Request){
 if(!isAdmin(request)||!sameOrigin(request))return json({error:'Forbidden'},403);
 if(Number(request.headers.get('content-length'))>11*1024*1024)return json({error:'Image exceeds 10 MB'},413);
 try{const form=await request.formData();const file=form.get('file');if(!file||typeof file==='string'||!file.size||file.size>10*1024*1024)return json({error:'Select an image under 10 MB'},400);
 const bytes=new Uint8Array(await file.arrayBuffer());const ascii=(start:number,end:number)=>String.fromCharCode(...bytes.slice(start,end));
 let ext='',type='';if(bytes[0]===137&&ascii(1,4)==='PNG'&&bytes[4]===13&&bytes[5]===10&&bytes[6]===26&&bytes[7]===10){ext='png';type='image/png'}else if(bytes[0]===255&&bytes[1]===216&&bytes[2]===255){ext='jpg';type='image/jpeg'}else if(ascii(0,4)==='RIFF'&&ascii(8,12)==='WEBP'){ext='webp';type='image/webp'}else if(['GIF87a','GIF89a'].includes(ascii(0,6))){ext='gif';type='image/gif'}else return json({error:'Use PNG, JPG, WebP or GIF'},400);
 const key=crypto.randomUUID()+'.'+ext;await env.BUCKET.put('reward-covers/'+key,bytes,{httpMetadata:{contentType:type}});return json({url:'/media/'+key},201);
 }catch(e){console.error(e);return json({error:'Unable to upload cover'},503)}
}
