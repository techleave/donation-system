package org.hkvc.donate;

import java.util.*;
import java.time.Instant;

/** Administrator-only, transactional, idempotent import of the original Sites records. */
final class Migration {
    static final String SOURCE="appgprj_6abb452ba1388191badab398f5fb3b58";
    final Store store;
    Migration(Store store){this.store=store;}
    static String date(Map<String,Object> r,String key){String value=Application.string(r,key);try{Instant.parse(value);return value;}catch(Exception e){throw new Application.Failure(400,"Invalid record date");}}
    Map<String,Object> importData(Map<String,Object> body)throws Exception{
        Validation.require(SOURCE.equals(body.get("sourceProjectId")),"Invalid source project");
        var tables=Application.object(body.get("tables"));var donors=Application.list(tables.get("donors"));var entries=Application.list(tables.get("donor_point_entries"));var requests=Application.list(tables.get("reward_requests"));
        Validation.require(donors.size()<=1000&&entries.size()<=10000&&requests.size()<=10000,"Import exceeds limit");
        String digest=Auth.digest(Application.JSON.writeValueAsString(tables));
        store.exec("CREATE TABLE IF NOT EXISTS site_data_imports (source TEXT PRIMARY KEY,digest TEXT NOT NULL,counts TEXT NOT NULL,imported_at TEXT NOT NULL)");
        var previous=store.one("SELECT digest,counts FROM site_data_imports WHERE source=?",SOURCE);
        if(previous!=null){if(!digest.equals(previous.get("digest")))throw new Application.Failure(409,"This source has already been imported. Review changes before importing again.");return Application.map("alreadyImported",true,"counts",Application.JSON.readValue((String)previous.get("counts"),Map.class));}
        var donorIds=new HashSet<String>();var emails=new HashSet<Object>();
        for(Object raw:donors){var r=Application.object(raw);String id=Validation.id(r.get("id"));Validation.require(donorIds.add(id),"Duplicate donor identifier");var d=Validation.donor(Application.map("prefix",r.get("prefix"),"englishName",r.get("english_name"),"chineseName",r.get("chinese_name"),"phone",r.get("phone"),"email",r.get("email")));Validation.require(emails.add(d.get("email")),"Duplicate donor email");
            if(store.one("SELECT id FROM donors WHERE id=? OR email=?",id,d.get("email"))!=null)throw new Application.Failure(409,"A matching donor already exists. Import cancelled to preserve current data.");
            Validation.integer(r.get("points"),0,10000000,"Invalid balance");Validation.integer(r.get("revision"),1,Integer.MAX_VALUE,"Invalid revision");date(r,"created_at");date(r,"updated_at");Validation.require(r.get("photo_key")==null,"Export donor images before importing profiles with photos");}
        var ledgerIds=new HashSet<String>();for(Object raw:entries){var r=Application.object(raw);Validation.require(ledgerIds.add(Validation.id(r.get("id")))&&donorIds.contains(Validation.id(r.get("donor_id"))),"Invalid points link");Validation.integer(r.get("amount"),-10000000,10000000,"Invalid points entry");Validation.integer(r.get("applied"),0,1,"Invalid points entry");Validation.require(List.of("add","tree").contains(r.get("kind")),"Invalid points kind");date(r,"created_at");}
        var requestIds=new HashSet<String>();for(Object raw:requests){var r=Application.object(raw);Validation.require(requestIds.add(Validation.id(r.get("id"))),"Duplicate request identifier");Validation.id(r.get("receipt"));Validation.require(r.get("donor_id")==null||donorIds.contains(Validation.id(r.get("donor_id"))),"Invalid request profile");Validation.require(Validation.CATEGORIES.contains(r.get("category"))&&List.of("pending","complete").contains(r.get("status")),"Invalid request");date(r,"submitted_at");Application.object(Application.JSON.readValue(Application.string(r,"fields"),Map.class));for(String key:List.of("name","email","fields"))Validation.require(r.get(key) instanceof String&&((String)r.get(key)).length()<=200000,"Invalid request");}
        // Back up the actual destination, never a browser/local cache, before changing any donor data.
        String backup=store.root.resolve("before-sites-import-"+UUID.randomUUID()+".sqlite").toString();
        store.exec("VACUUM INTO '"+backup.replace("'","''")+"'");
        var counts=Application.map("donors",donors.size(),"pointEntries",entries.size(),"requests",requests.size());String now=Store.now();
        store.transaction(()->{
            for(Object raw:donors){var r=Application.object(raw);store.update("INSERT INTO donors (id,prefix,english_name,chinese_name,phone,email,photo_key,user_id,revision,created_at,updated_at,points) VALUES (?,?,?,?,?,?,NULL,NULL,?,?,?,?)",r.get("id"),r.get("prefix"),r.get("english_name"),r.get("chinese_name"),r.get("phone"),Application.string(r,"email").toLowerCase(Locale.ROOT),r.get("revision"),r.get("created_at"),r.get("updated_at"),r.get("points"));}
            for(Object raw:entries){var r=Application.object(raw);store.update("INSERT INTO donor_point_entries (id,donor_id,amount,kind,created_at,applied) VALUES (?,?,?,?,?,?)",r.get("id"),r.get("donor_id"),r.get("amount"),r.get("kind"),r.get("created_at"),r.get("applied"));}
            for(Object raw:requests){var r=Application.object(raw);store.update("INSERT INTO reward_requests (id,receipt,name,email,category,fields,submitted_at,status,donor_id) VALUES (?,?,?,?,?,?,?,?,?)",r.get("id"),r.get("receipt"),r.get("name"),r.get("email"),r.get("category"),r.get("fields"),r.get("submitted_at"),r.get("status"),r.get("donor_id"));}
            store.update("INSERT INTO site_data_imports VALUES (?,?,?,?)",SOURCE,digest,Application.JSON.writeValueAsString(counts),now);return null;
        });return Application.map("alreadyImported",false,"counts",counts,"importedAt",now);
    }
}
