package org.hkvc.donate;

import com.sun.net.httpserver.HttpExchange;
import io.nayuki.qrcodegen.QrCode;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static org.hkvc.donate.Application.*;

/** Private, per-tree fulfilment links. QR codes are generated locally. */
final class TreeAdoptions {
    final Application app;
    TreeAdoptions(Application app)throws Exception{
        this.app=app;
        app.store.exec("CREATE TABLE IF NOT EXISTS tree_adoptions (request_id TEXT NOT NULL REFERENCES reward_requests(id) ON DELETE CASCADE,tree_index INTEGER NOT NULL,url TEXT NOT NULL,label TEXT NOT NULL,revision INTEGER NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(request_id,tree_index))");
    }
    Map<String,Object> request(String id,Map<String,Object> user)throws Exception{
        var r=app.store.one("SELECT id,donor_id,category,fields,status,submitted_at FROM reward_requests WHERE id=?",id);
        if(r==null||!"tree".equals(r.get("category")))throw new Failure(404,"Tree request not found");
        var donor=app.own(user);if(!app.auth.admin(user)&&(donor==null||!donor.get("id").equals(r.get("donor_id"))))throw new Failure(403,"Forbidden");
        return r;
    }
    long quantity(Map<String,Object> request)throws Exception{return Donations.quantity(object(JSON.readValue((String)request.get("fields"),Map.class)),"tree");}
    void handle(HttpExchange e,String method,Map<String,String> p,Map<String,Object> user,boolean qr)throws Exception{
        if(user==null)throw new Failure(401,"Sign in required");
        if(qr){
            if(!method.equals("GET"))throw new Failure(405,"Method not allowed");String id=Validation.id(p.get("requestId"));request(id,user);int index;try{index=Integer.parseInt(p.getOrDefault("index","0"));}catch(Exception ex){throw new Failure(400,"Invalid tree index");}
            var row=app.store.one("SELECT url FROM tree_adoptions WHERE request_id=? AND tree_index=?",id,index);if(row==null)throw new Failure(404,"Tree link not assigned yet");
            e.getResponseHeaders().set("Cache-Control","private, no-store");bytes(e,200,svg((String)row.get("url")).getBytes(StandardCharsets.UTF_8),"image/svg+xml; charset=utf-8");return;
        }
        if(method.equals("GET")){
            if(p.containsKey("requestId")){String id=Validation.id(p.get("requestId"));var r=request(id,user);json(e,200,map("requestId",id,"quantity",quantity(r),"trees",app.store.all("SELECT tree_index AS treeIndex,url,label,revision,updated_at AS updatedAt FROM tree_adoptions WHERE request_id=? ORDER BY tree_index",id)));return;}
            var donor=app.own(user);if(donor==null)throw new Failure(403,"Donor profile required");var groups=new ArrayList<Object>();
            for(var r:app.store.all("SELECT id,fields,status,submitted_at FROM reward_requests WHERE donor_id=? AND category='tree' AND status NOT IN ('cancelled','rejected') ORDER BY submitted_at DESC,id",donor.get("id"))){var rows=app.store.all("SELECT tree_index AS treeIndex,url,label,revision,updated_at AS updatedAt FROM tree_adoptions WHERE request_id=? ORDER BY tree_index",r.get("id"));groups.add(map("requestId",r.get("id"),"quantity",quantity(r),"submittedAt",r.get("submitted_at"),"status",r.get("status"),"trees",rows));}
            json(e,200,map("adoptions",groups));return;
        }
        if(!method.equals("POST"))throw new Failure(405,"Method not allowed");app.admin(e,user,true);var b=bodyJson(e);String id=Validation.id(b.get("requestId"));var r=request(id,user);
        if(List.of("cancelled","rejected").contains(r.get("status")))throw new Failure(409,"Request is inactive");
        int index=Validation.integer(b.get("treeIndex"),1,(int)quantity(r),"Choose a tree in this request"),revision=Validation.integer(b.get("revision"),0,Integer.MAX_VALUE-1,"Invalid revision");
        String url=string(b,"url").trim(),label=string(b,"label").trim();Validation.require(label.length()<=120,"Tree label is too long");
        try{var u=new URI(url);Validation.require(url.length()<=2048&&"https".equalsIgnoreCase(u.getScheme())&&u.getHost()!=null&&u.getRawUserInfo()==null,"Use a complete HTTPS tree link");svg(url);}catch(Failure f){throw f;}catch(Exception ex){throw new Failure(400,"Invalid tree link or link is too long for a QR code");}
        String now=Store.now();int changed=revision==0?app.store.update("INSERT OR IGNORE INTO tree_adoptions VALUES (?,?,?,?,1,?)",id,index,url,label,now):app.store.update("UPDATE tree_adoptions SET url=?,label=?,revision=revision+1,updated_at=? WHERE request_id=? AND tree_index=? AND revision=?",url,label,now,id,index,revision);
        if(changed==0)throw new Failure(409,"This tree link changed. Reopen the editor before saving.");
        json(e,200,map("ok",true,"revision",revision+1));
    }
    static String svg(String url){
        var qr=QrCode.encodeText(url,QrCode.Ecc.MEDIUM);int border=4,size=qr.size+border*2;var path=new StringBuilder();
        for(int y=0;y<qr.size;y++)for(int x=0;x<qr.size;x++)if(qr.getModule(x,y))path.append('M').append(x+border).append(',').append(y+border).append("h1v1h-1z");
        return "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 "+size+" "+size+"\" shape-rendering=\"crispEdges\"><rect width=\"100%\" height=\"100%\" fill=\"white\"/><path d=\""+path+"\" fill=\"#163e2c\"/></svg>";
    }
}
