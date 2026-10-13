package org.hkvc.donate;

import java.sql.*;
import java.nio.file.*;
import java.util.*;
import java.time.Instant;

/** One connection guarded by Application's transaction lock; no cross-request transaction mixing. */
final class Store implements AutoCloseable {
    final Connection db;
    final Path root;
    Store(String directory) throws Exception {
        root=Path.of(directory).toAbsolutePath().normalize(); Files.createDirectories(root.resolve("objects"));
        Class.forName("org.sqlite.JDBC"); db=DriverManager.getConnection("jdbc:sqlite:"+root.resolve("donate.sqlite"));
        exec("PRAGMA journal_mode=WAL"); exec("PRAGMA foreign_keys=ON"); exec("PRAGMA busy_timeout=5000");
        exec("CREATE TABLE IF NOT EXISTS runtime_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)");
        for(String name:List.of("0000_dear_kronos.sql","0001_eminent_veda.sql","0002_unique_wendell_rand.sql")) {
            if(one("SELECT name FROM runtime_migrations WHERE name=?",name)!=null) continue;
            transaction(()->{for(String sql:Application.resourceText("drizzle/"+name).split(";")) if(!sql.isBlank()) exec(sql);
                update("INSERT INTO runtime_migrations VALUES (?,?)",name,now()); return null;});
        }
        exec("CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','donor')),donor_id TEXT UNIQUE REFERENCES donors(id) ON DELETE CASCADE)");
        exec("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,expires_at INTEGER NOT NULL)");
    }
    static String now(){return Instant.now().toString();}
    void exec(String sql)throws SQLException{try(var s=db.createStatement()){s.execute(sql);}}
    PreparedStatement prepare(String sql,Object... args)throws SQLException{var p=db.prepareStatement(sql); for(int i=0;i<args.length;i++) p.setObject(i+1,args[i]);return p;}
    int update(String sql,Object... args)throws SQLException{try(var p=prepare(sql,args)){return p.executeUpdate();}}
    List<Map<String,Object>> all(String sql,Object... args)throws SQLException{
        try(var p=prepare(sql,args);var r=p.executeQuery()){var out=new ArrayList<Map<String,Object>>();var m=r.getMetaData();
            while(r.next()){var row=new LinkedHashMap<String,Object>();for(int i=1;i<=m.getColumnCount();i++)row.put(m.getColumnLabel(i),r.getObject(i));out.add(row);}return out;}
    }
    Map<String,Object> one(String sql,Object... args)throws SQLException{var list=all(sql,args);return list.isEmpty()?null:list.get(0);}
    interface Work<T>{T run()throws Exception;}
    <T>T transaction(Work<T> action)throws Exception{
        exec("BEGIN IMMEDIATE");try{T result=action.run();exec("COMMIT");return result;}catch(Exception e){exec("ROLLBACK");throw e;}
    }
    Path object(String key){if(!key.matches("[a-zA-Z0-9/_\\-.]+")||Arrays.asList(key.split("/")).contains(".."))throw new IllegalArgumentException("Invalid key");
        var path=root.resolve("objects").resolve(key).normalize();if(!path.startsWith(root.resolve("objects")))throw new IllegalArgumentException("Invalid key");return path;}
    void put(String key,byte[] data)throws Exception{var p=object(key);Files.createDirectories(p.getParent());var tmp=p.resolveSibling(p.getFileName()+"."+UUID.randomUUID()+".tmp");Files.write(tmp,data);Files.move(tmp,p,StandardCopyOption.ATOMIC_MOVE);}
    void delete(String key)throws Exception{if(key==null)return;Files.deleteIfExists(object(key));Files.deleteIfExists(object(key+".meta.json"));}
    public void close()throws SQLException{db.close();}
}
