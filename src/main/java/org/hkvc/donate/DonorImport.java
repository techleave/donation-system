package org.hkvc.donate;

import java.util.*;
import java.nio.charset.StandardCharsets;
import java.io.*;
import java.util.zip.*;
import javax.xml.parsers.*;
import org.w3c.dom.*;
import static org.hkvc.donate.Application.*;

/** Preview and apply use the same plan. Money and import receipts commit together. */
final class DonorImport {
 final Application app;final Store store;
 DonorImport(Application app)throws Exception{this.app=app;store=app.store;
  store.transaction(()->{store.exec("CREATE TABLE IF NOT EXISTS donor_import_keys (identity_key TEXT PRIMARY KEY,donor_id TEXT NOT NULL REFERENCES donors(id) ON DELETE CASCADE)");
   store.exec("CREATE TABLE IF NOT EXISTS donor_import_receipts (operation_key TEXT PRIMARY KEY,donor_id TEXT NOT NULL REFERENCES donors(id) ON DELETE CASCADE,created_at TEXT NOT NULL)");
   if(store.one("SELECT name FROM runtime_migrations WHERE name='blank-donor-email-v1'")==null){store.exec("DROP INDEX IF EXISTS donors_email_unique");store.exec("CREATE UNIQUE INDEX donors_email_unique ON donors(email) WHERE email<>''");store.update("INSERT INTO runtime_migrations VALUES ('blank-donor-email-v1',?)",Store.now());}return null;});
 }
 static String cell(List<String> row,int i){return i<0||i>=row.size()?"":row.get(i).trim();}
 static String norm(String s){return s.toLowerCase(Locale.ROOT).replaceAll("[\\s_\\-().（）]","");}
 static int column(List<String> h,String... aliases){int found=-1;for(int i=0;i<h.size();i++)if(Arrays.asList(aliases).contains(norm(h.get(i)))){Validation.require(found<0,"Duplicate column: "+h.get(i));found=i;}return found;}
 static String id(String s){return UUID.nameUUIDFromBytes(s.getBytes(StandardCharsets.UTF_8)).toString();}
 Map<String,Object> run(Map<String,Object> body,boolean apply)throws Exception{
  String csv=body.get("xlsx") instanceof String?xlsx((String)body.get("xlsx")):string(body,"csv");
  var raw=Validation.csv(csv);var h=raw.get(0);
  int name=column(h,"姓名","name","fullname","englishfullname","englishname","英文姓名","英文全名"),chinese=column(h,"中文姓名","中文全名","chinesefullname","chinesename"),prefix=column(h,"prefix","title","sal","salutation","稱謂","称谓"),phone=column(h,"電話","电话","phone","telephone","tel","mobile","contactnumber","contactno"),email=column(h,"郵箱","邮箱","電郵","電子郵件","email","emailaddress"),address=column(h,"個人地址","个人地址","郵寄地址","地址","address","personaladdress","deliveryaddress");
  int total=column(h,"捐款總額hkd","捐款总额hkd","捐款總額","捐款总额","累計捐款","累计捐款","累計捐款總額","累计捐款总额","cumulativedonation","cumulativedonationhkd","totaldonation","totaldonated"),date=column(h,"最新捐款日期","捐款日期","donationdate","lastdonationdate","donatedon","date");
  Validation.require(name>=0||chinese>=0,"Include a name column / 請提供姓名欄");
  var plans=new ArrayList<Map<String,Object>>();var seen=new HashSet<String>();var seenDonors=new HashSet<String>();int skipped=0,missing=0,newCount=0,updated=0,duplicate=0,donationUpdates=0;long increase=0;
  for(int r=1;r<raw.size();r++){
   var row=raw.get(r);Validation.require(row.size()<=h.size(),"Too many columns in row "+(r+1));
   String n=cell(row,name),cn=cell(row,chinese),em=cell(row,email).toLowerCase(Locale.ROOT),ph=cell(row,phone),ad=postalAddress(cell(row,address));
   Validation.require(em.isBlank()||em.matches("[^\\s@]+@[^\\s@]+\\.[^\\s@]+"),"Invalid email at row "+(r+1));Validation.require(!n.matches("(?s).*[\\x00-\\x1f].*")&&!cn.matches("(?s).*[\\x00-\\x1f].*")&&!ph.matches("(?s).*[\\x00-\\x1f].*"),"Invalid name or phone at row "+(r+1));Validation.require(n.length()<=150&&cn.length()<=100&&ph.length()<=50&&em.length()<=180&&cell(row,prefix).length()<=40,"Text too long at row "+(r+1));
   String identity=!em.isBlank()?"email:"+em:!ph.isBlank()?"phone:"+ph.replaceAll("[\\s()-]",""):!n.isBlank()||!cn.isBlank()?"name:"+n+":"+cn:"";
   if(identity.isBlank()){missing++;continue;}Validation.require(seen.add(identity),"Duplicate person in file at row "+(r+1)+" / 表內有重複資料，請合併後匯入");
   var old=em.isBlank()?null:store.one("SELECT * FROM donors WHERE email=?",em);
   // A previously unregistered donor can be linked once an email is supplied.
   if(old==null&&!ph.isBlank()){var candidates=em.isBlank()?store.all("SELECT * FROM donors WHERE phone=?",ph):store.all("SELECT * FROM donors WHERE email='' AND phone=?",ph);Validation.require(candidates.size()<=1,"More than one donor has this phone. Add the email in User Management first.");if(candidates.size()==1)old=candidates.get(0);}
   if(old==null&&!em.isBlank()&&ph.isBlank()&&!n.isBlank()){var candidates=store.all("SELECT * FROM donors WHERE email='' AND english_name=?",n);Validation.require(candidates.size()<=1,"More than one unregistered donor has this name. Add the email in User Management first.");if(candidates.size()==1)old=candidates.get(0);}
   if(old==null){var key=store.one("SELECT donor_id FROM donor_import_keys WHERE identity_key=?",identity);if(key!=null)old=app.donorById(key.get("donor_id"));}
   if(old!=null)Validation.require(seenDonors.add((String)old.get("id")),"The same donor appears twice in the file. Merge those rows first.");
   long before=old==null?0:app.donations.total(old.get("id"));String tv=cell(row,total),dv=cell(row,date);long initial=tv.isBlank()?0:Donations.money(tv);String donated=dv.isBlank()?"":Donations.date(dv);
   String donorId=old==null?UUID.randomUUID().toString():(String)old.get("id");
   String operation=id("donor-cumulative-import-v3:"+identity+":"+initial);
   boolean repeated=store.one("SELECT operation_key FROM donor_import_receipts WHERE operation_key=?",operation)!=null;
   long after=old==null?initial:tv.isBlank()?before:Math.max(before,initial);
   if(total>=0&&!tv.isBlank()&&initial<500000||old==null&&total>=0&&after<500000){skipped++;continue;}
   if(old==null)newCount++;else updated++;if(repeated)duplicate++;if(after>before){donationUpdates++;increase+=after-before;}
   plans.add(map("id",donorId,"old",old,"identity",identity,"operation",operation,"repeated",repeated,"prefix",cell(row,prefix),"englishName",n,"chineseName",cn,"phone",ph,"email",em,"address",ad,"donationMinor",after,"additionalMinor",Math.max(0,after-before),"donationDate",donated,"before",before,"newPoints",(after/500000-before/500000)*1000));
  }
  var result=map("total",raw.size()-1,"added",newCount,"updated",updated,"skippedBelowMinimum",skipped,"skippedMissingIdentity",missing,"duplicates",duplicate,"donationUpdates",donationUpdates,"skippedLower",0,"unchangedDonations",plans.size()-donationUpdates,"addedDonation",java.math.BigDecimal.valueOf(increase,2));
  result.put("preview",plans.stream().limit(20).map(p->map("englishName",p.get("englishName"),"chineseName",p.get("chineseName"),"phone",p.get("phone"),"email",p.get("email"),"address",p.get("address"),"donationMinor",p.get("donationMinor"),"additionalMinor",p.get("additionalMinor"),"donationDate",p.get("donationDate"),"newPoints",p.get("newPoints"))).toList());
  if(apply)store.transaction(()->{for(var p:plans){String donorId=(String)p.get("id");var old=(Map<String,Object>)p.get("old");String now=Store.now();
   if(old==null)store.update("INSERT INTO donors (id,prefix,english_name,chinese_name,phone,email,address,revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,1,?,?)",donorId,p.get("prefix"),p.get("englishName"),p.get("chineseName"),p.get("phone"),p.get("email"),p.get("address"),now,now);
   else{String[] keys={"prefix","englishName","chineseName","phone","email","address"},cols={"prefix","english_name","chinese_name","phone","email","address"};var values=new ArrayList<Object>();for(int i=0;i<keys.length;i++)values.add(string(p,keys[i]).isBlank()?old.get(cols[i]):p.get(keys[i]));values.add(now);values.add(donorId);store.update("UPDATE donors SET prefix=?,english_name=?,chinese_name=?,phone=?,email=?,address=?,revision=revision+1,updated_at=? WHERE id=?",values.toArray());}
   store.update("INSERT OR IGNORE INTO donor_import_keys VALUES (?,?)",p.get("identity"),donorId);
   if(!Boolean.TRUE.equals(p.get("repeated"))){long amount=((Number)p.get("donationMinor")).longValue();if(amount>((Number)p.get("before")).longValue())app.donations.snapshot((String)p.get("operation"),donorId,amount,(String)p.get("donationDate"),"spreadsheet-import",false);store.update("INSERT INTO donor_import_receipts VALUES (?,?,?)",p.get("operation"),donorId,now);}
  }return null;});return result;
 }
 static Document xml(byte[] b)throws Exception{var f=DocumentBuilderFactory.newInstance();f.setFeature("http://apache.org/xml/features/disallow-doctype-decl",true);f.setFeature("http://xml.org/sax/features/external-general-entities",false);f.setFeature("http://xml.org/sax/features/external-parameter-entities",false);f.setXIncludeAware(false);f.setExpandEntityReferences(false);return f.newDocumentBuilder().parse(new ByteArrayInputStream(b));}
 static String text(Element e,String tag){var n=e.getElementsByTagName(tag);var s=new StringBuilder();for(int i=0;i<n.getLength();i++)s.append(n.item(i).getTextContent());return s.toString();}
 static String xlsx(String encoded)throws Exception{
  byte[] bytes;try{bytes=Base64.getDecoder().decode(encoded);}catch(Exception e){throw new Failure(400,"Invalid Excel file");}Validation.require(bytes.length<=2*1024*1024,"Excel exceeds 2 MB");
  var parts=new HashMap<String,byte[]>();int expanded=0,count=0;
  try(var z=new ZipInputStream(new ByteArrayInputStream(bytes))){for(ZipEntry e;(e=z.getNextEntry())!=null;){Validation.require(++count<=2500,"Excel has too many parts");byte[] data=z.readNBytes(16*1024*1024+1);expanded+=data.length;Validation.require(data.length<=16*1024*1024&&expanded<=24*1024*1024,"Excel is too large when expanded");if(e.getName().startsWith("xl/"))parts.put(e.getName(),data);}}
  var strings=new ArrayList<String>();if(parts.containsKey("xl/sharedStrings.xml")){var nodes=xml(parts.get("xl/sharedStrings.xml")).getElementsByTagName("si");for(int i=0;i<nodes.getLength();i++)strings.add(text((Element)nodes.item(i),"t"));}
  Validation.require(parts.containsKey("xl/worksheets/sheet1.xml"),"Excel needs a first worksheet");var doc=xml(parts.get("xl/worksheets/sheet1.xml"));var rows=doc.getElementsByTagName("row");var out=new StringBuilder();var all=new ArrayList<List<String>>();int width=0;
  for(int i=0;i<rows.getLength();i++){var row=(Element)rows.item(i);var cells=row.getElementsByTagName("c");var values=new ArrayList<String>();for(int j=0;j<cells.getLength();j++){var c=(Element)cells.item(j);Validation.require(c.getElementsByTagName("f").getLength()==0,"Excel formulas are not supported. Paste values before uploading.");String ref=c.getAttribute("r"),letters=ref.replaceAll("[0-9]","");int col=0;for(char ch:letters.toCharArray())col=col*26+ch-'A'+1;Validation.require(col>0&&col<=100,"Too many Excel columns");while(values.size()<col)values.add("");String type=c.getAttribute("t"),v=type.equals("inlineStr")?text(c,"t"):text(c,"v");if(type.equals("s"))v=strings.get(Integer.parseInt(v));values.set(col-1,v);}if(values.stream().anyMatch(v->!v.isBlank())){if(all.isEmpty())width=values.size();while(values.size()>width&&values.get(values.size()-1).isBlank())values.remove(values.size()-1);while(values.size()<width)values.add("");all.add(values);}Validation.require(all.size()<=501,"Maximum 500 donors per upload");}
  // Excel dates are serial values. Convert only the donation-date column.
  if(!all.isEmpty()){int d=column(all.get(0),"最新捐款日期","捐款日期","donationdate","lastdonationdate","date");for(int i=1;i<all.size();i++)if(d>=0&&d<all.get(i).size()){String v=all.get(i).get(d);if(v.matches("[0-9]+(\\.0+)?")){long days=new java.math.BigDecimal(v).longValueExact();all.get(i).set(d,java.time.LocalDate.of(1899,12,30).plusDays(days).toString());}}}
  for(var row:all){out.append(row.stream().map(v->"\""+v.replace("\"","\"\"")+"\"").collect(java.util.stream.Collectors.joining(","))).append('\n');}return out.toString();
 }
}
