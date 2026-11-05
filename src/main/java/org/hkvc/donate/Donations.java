package org.hkvc.donate;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import static org.hkvc.donate.Application.*;

/** Donations are money; each reward has its own lifetime allowance and usage. */
final class Donations {
    final Store store;
    Donations(Store store)throws Exception{
        this.store=store;
        if(store.one("SELECT name FROM runtime_migrations WHERE name='donation-entitlements-v1'")!=null)return;
        // Keep a recoverable copy before introducing the new accounting tables.
        var backup=store.root.resolve("before-donation-entitlements-"+UUID.randomUUID()+".sqlite");
        store.exec("VACUUM INTO '"+backup.toString().replace("'","''")+"'");
        store.transaction(()->{
            store.exec("CREATE TABLE donation_balances (donor_id TEXT PRIMARY KEY REFERENCES donors(id) ON DELETE CASCADE,total_minor INTEGER NOT NULL CHECK(total_minor>=0))");
            store.exec("CREATE TABLE donation_entries (id TEXT PRIMARY KEY,donor_id TEXT NOT NULL REFERENCES donors(id) ON DELETE CASCADE,amount_minor INTEGER NOT NULL,delta_minor INTEGER NOT NULL,total_minor INTEGER NOT NULL,donated_on TEXT NOT NULL,created_at TEXT NOT NULL,source TEXT NOT NULL)");
            store.exec("CREATE INDEX donation_entries_donor ON donation_entries(donor_id,created_at)");
            store.exec("CREATE INDEX IF NOT EXISTS reward_requests_donor ON reward_requests(donor_id)");
            store.update("INSERT INTO runtime_migrations VALUES ('donation-entitlements-v1',?)",Store.now());return null;
        });
    }
    static long money(Object value){
        try{String text=String.valueOf(value).trim();
            Validation.require(!text.contains(",")||text.matches("[0-9]{1,3}(,[0-9]{3})+(\\.[0-9]{1,2})?"),"Invalid thousands separators in donation amount");
            var n=new BigDecimal(text.replace(",","")).setScale(2,RoundingMode.UNNECESSARY);
            Validation.require(n.signum()>=0&&n.compareTo(new BigDecimal("1000000000"))<=0,"Enter an HKD amount between 0 and 1,000,000,000, with at most two decimal places");return n.movePointRight(2).longValueExact();
        }catch(Failure f){throw f;}catch(Exception e){throw new Failure(400,"Invalid donation amount");}
    }
    static String date(Object value){
        String s=String.valueOf(value).trim();
        for(var format:List.of(DateTimeFormatter.ISO_LOCAL_DATE,DateTimeFormatter.ofPattern("d/M/uuuu").withResolverStyle(java.time.format.ResolverStyle.STRICT)))
            try{return LocalDate.parse(s,format).toString();}catch(Exception ignored){}
        throw new Failure(400,"Donation date must be YYYY-MM-DD or DD/MM/YYYY");
    }
    long total(Object id)throws Exception{var row=store.one("SELECT total_minor FROM donation_balances WHERE donor_id=?",id);return row==null?0:((Number)row.get("total_minor")).longValue();}
    static long quantity(Map<String,Object> fields,String category){
        Object raw=fields.get(category.equals("tree")?"leaves":"quantity");
        if(raw instanceof Map<?,?> f)raw=f.get("value");
        try{long n=new BigDecimal(String.valueOf(raw)).longValueExact();if(n>=1&&n<=10000000)return n;}catch(Exception ignored){}
        return 1; // Historical requests without a quantity represent one redemption.
    }
    Map<String,Object> summary(Object id)throws Exception{
        long total=total(id),units=total/500000;var used=new HashMap<String,Long>();
        for(var r:store.all("SELECT category,fields FROM reward_requests WHERE donor_id=?",id)){
            String category=(String)r.get("category");var fields=object(JSON.readValue((String)r.get("fields"),Map.class));
            used.merge(category,quantity(fields,category),Long::sum);
        }
        var rewards=new LinkedHashMap<String,Object>();
        for(String category:Validation.CATEGORIES){long earned=category.equals("ticket")?(total>=5000000?2:total>=500000?1:0):units;
            long redeemed=used.getOrDefault(category,0L);rewards.put(category,map("earned",earned,"used",redeemed,"remaining",Math.max(0,earned-redeemed)));}
        return map("cumulativeDonation",BigDecimal.valueOf(total,2),"cumulativePoints",units*1000,"entitlements",rewards);
    }
    void reserve(Object donorId,String category,int quantity)throws Exception{
        var summary=summary(donorId);var reward=object(object(summary.get("entitlements")).get(category));
        if(((Number)reward.get("remaining")).longValue()<quantity)throw new Failure(409,"此項權益剩餘次數不足 / No remaining allowance for this reward. Reload your profile.");
    }
    /** Set a cumulative snapshot, never add the snapshot to a previous total. */
    boolean snapshot(String id,String donorId,long amount,String date,String source,boolean allowDecrease)throws Exception{
        var previous=store.one("SELECT * FROM donation_entries WHERE id=?",id);
        if(previous!=null){if(!donorId.equals(previous.get("donor_id"))||((Number)previous.get("amount_minor")).longValue()!=amount||!date.equals(previous.get("donated_on")))throw new Failure(409,"Donation operation identifier already used");return false;}
        long before=total(donorId);
        if(amount==before)return false;
        if(amount<before&&!allowDecrease)return false;
        store.update("INSERT INTO donation_entries VALUES (?,?,?,?,?,?,?,?)",id,donorId,amount,amount-before,amount,date,Store.now(),source);
        store.update("INSERT INTO donation_balances VALUES (?,?) ON CONFLICT(donor_id) DO UPDATE SET total_minor=excluded.total_minor",donorId,amount);
        store.update("UPDATE donors SET revision=revision+1,updated_at=? WHERE id=?",Store.now(),donorId);return true;
    }
    static List<Map<String,Object>> csv(String text){
        var rows=Validation.donorCsv(text);var raw=Validation.csv(text);var headers=raw.get(0);
        int amount=-1,date=-1;
        for(int i=0;i<headers.size();i++){
            String h=headers.get(i).trim().toLowerCase(Locale.ROOT).replaceAll("[\\s_\\-().]","");
            if(List.of("cumulativedonation","totaldonated","totaldonation","cumulativedonationhkd","累計捐款","累计捐款","累計捐款總額","累计捐款总额").contains(h)){Validation.require(amount<0,"Duplicate cumulative donation column");amount=i;}
            if(List.of("donationdate","donatedon","date","捐款日期").contains(h)){Validation.require(date<0,"Duplicate donation date column");date=i;}
        }
        Validation.require(amount<0||date>=0,"Include Donation Date when importing Cumulative Donation");
        for(int i=0;i<rows.size();i++){
            var row=rows.get(i);
            if(amount>=0){String v=raw.get(i+1).get(amount).trim();Validation.require(!v.isEmpty(),"CSV row "+(i+2)+": cumulative donation is required");
                row.put("donationMinor",money(v));row.put("donationDate",date(raw.get(i+1).get(date)));}
        }
        return rows;
    }
}
