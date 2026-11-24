/* Public, no-key sources only. No AI calls, image uploads or inferred nutrients. */
(function(root){
'use strict';
const AMINO=['Alanine','Arginine','Aspartic','Cystine','Glutamine','Glycine','Histidine','Isoleucine','Leucine','Lysine','Methionine','Phenylalanine','Proline','Serine','Threonine','Tryptophan','Tyrosine','Valine'];
const aliases={Aspartic:'aspartic-acid',Cystine:'cystine',Glutamine:'glutamic-acid'};
const num=v=>{if(v===null||v===undefined||v==='')return null;const n=Number(v);return Number.isFinite(n)&&n>=0?n:null;};
const same=(a,b)=>/^\d{8,14}$/.test(a)&&/^\d{8,14}$/.test(b)&&a.padStart(14,'0')===b.padStart(14,'0');
function valid(code){if(!/^(\d{8}|\d{12,14})$/.test(code))return false;let n=0;for(let i=code.length-2,m=3;i>=0;i--,m=4-m)n+=Number(code[i])*m;return (10-n%10)%10===Number(code.at(-1));}
function empty(name,url,source){return {name,source,url,serving_g:null,protein_g:null,sugar_g:null,amino:{},unit:'serving',summary:{},added:[],retrieved_at:new Date().toISOString(),basis:'per serving',warnings:[]};}
function fromOFF(p,code){
 if(p.code&&!same(String(p.code),code))return null;
 const o=empty([p.brands,p.product_name].filter(Boolean).join(' '),'https://world.openfoodfacts.org/api/v2/product/'+code+'.json','Open Food Facts');
 const q=num(p.serving_quantity);o.serving_g=q>0&&q<=300&&(!p.serving_quantity_unit||p.serving_quantity_unit==='g')?q:null;
 const n=p.nutriments||{};
 function val(k){let v=num(n[k+'_serving']);if(v===null&&o.serving_g!==null){const x=num(n[k+'_100g']);if(x!==null)v=x*o.serving_g/100;}return v!==null&&o.serving_g!==null&&v>o.serving_g?null:v;}
 o.protein_g=o.serving_g?val('proteins'):null;o.sugar_g=o.serving_g?val('sugars'):null;
 AMINO.forEach(k=>{const v=val(aliases[k]||k.toLowerCase());if(v!==null)o.amino[k]=Math.round(v*1000*1000)/1000;});
 o.warnings.push('بيانات يضيفها المستخدمون. راجع الاسم والنكهة وحجم الحصة مع العبوة.');
 if(!o.serving_g&&Object.keys(o.amino).length){o.amino={};o.warnings.push('لم يتأكد حجم الحصة، لذلك لم نملأ الأحماض.');}
 return o.name||o.protein_g!==null||Object.keys(o.amino).length?o:null;
}
function fromNIH(p,code){
 const digits=String(p.upcSku||'').replace(/[\s-]/g,'');
 if(!same(digits,code)||p.offMarket!==0)return null;
 const sizes=(p.servingSizes||[]).filter(s=>s.inSFB&&s.minQuantity===s.maxQuantity);
 if(sizes.length!==1)return null;const s=sizes[0];
 const o=empty([p.brandName,p.fullName].filter(Boolean).join(' '),'https://api.ods.od.nih.gov/dsld/v9/label/'+encodeURIComponent(p.id),'NIH DSLD');
 o.label_id=p.id;o.label_date=p.entryDate||null;
 if(/^(g|gram\(s\)|grams?)$/i.test(s.unit)&&num(s.minQuantity)>0&&num(s.minQuantity)<=300)o.serving_g=num(s.minQuantity);
 const map={Protein:'protein_g',Sugar:'sugar_g','Total Sugars':'sugar_g',Sugars:'sugar_g'};
 function rows(list){for(const r of list||[]){
  const qs=(r.quantity||[]).filter(q=>q.servingSizeOrder===s.order&&q.operator==='='&&q.servingSizeQuantity===s.minQuantity&&q.servingSizeUnit===s.unit);
  if(qs.length===1){const q=qs[0],v=num(q.quantity),u=String(q.unit||'').toLowerCase();const g=/^(g|gram\(s\)|grams?)$/.test(u)?v:u==='mg'&&v!==null?v/1000:null;
   const key=String(r.name||'').replace(/^L-/i,'');
   if(g!==null&&(!o.serving_g||g<=o.serving_g)){
    if(map[key])o[map[key]]=g;
    if(AMINO.includes(key))o.amino[key]=g*1000;
    if(key==='Glutamic Acid'||key==='Glutamic acid')o.amino.Glutamine=g*1000;
    if(key==='Aspartic Acid'||key==='Aspartic acid')o.amino.Aspartic=g*1000;
   }
  }rows(r.nestedRows);
 }}rows(p.ingredientRows);
 o.warnings.push('سجل ملصق، وليس تأكيدًا أن تركيبة العبوة الحالية لم تتغير. راجع النكهة والحصة.');
 if(!o.serving_g)o.amino={};
 return o;
}
async function get(url,fetcher){const ctrl=new AbortController();const timer=setTimeout(()=>ctrl.abort(),9000);try{const r=await fetcher(url,{signal:ctrl.signal});if(r.status===404)return null;if(!r.ok)throw Error('source_unavailable');return await r.json();}finally{clearTimeout(timer);}}
async function lookup(code,fetcher=root.fetch.bind(root)){
 if(!valid(code))throw Error('invalid_barcode');
 let off=null,errors=[],candidates=[];
 try{const j=await get('https://world.openfoodfacts.org/api/v2/product/'+code+'.json',fetcher);if(j&&j.status===1)off=fromOFF(j.product,code);}catch(e){errors.push('Open Food Facts');}
 // A second source never silently patches values into another label.
 if(!off||off.serving_g===null||off.protein_g===null||Object.keys(off.amino).length<AMINO.length){
 try{
  const forms=[code];if(code.length===12)forms.push(code[0]+' '+code.slice(1,6)+' '+code.slice(6,11)+' '+code[11]);
  let j=null;for(const form of forms.reverse()){j=await get('https://api.ods.od.nih.gov/dsld/v9/search-filter?q='+encodeURIComponent('"'+form+'"')+'&size=5&status=1',fetcher);if(j&&j.hits&&j.hits.length)break;}
  const ids=[...new Set(((j&&j.hits)||[]).map(x=>String(x._id)).filter(x=>/^\d+$/.test(x)))];
  const labels=await Promise.all(ids.map(id=>get('https://api.ods.od.nih.gov/dsld/v9/label/'+id,fetcher)));for(const label of labels){const p=label&&fromNIH(label,code);if(p)candidates.push(p);}
  if(j&&j.stats&&j.stats.count>5){candidates=[];errors.push('نتائج NIH كثيرة، لم نختار أول نتيجة تلقائيًا');}
 }catch(e){errors.push('NIH DSLD');}
 }
 if(off)candidates.unshift(off);
 // Deduplicate same source records only; never merge formulas or dates.
 return {candidates,errors,code,incomplete:true};
}
root.NutraXProductFacts={AMINO,valid,same,fromOFF,fromNIH,lookup};
if(typeof module!=='undefined')module.exports=root.NutraXProductFacts;
})(typeof window!=='undefined'?window:globalThis);
