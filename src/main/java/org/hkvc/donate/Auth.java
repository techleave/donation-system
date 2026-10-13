package org.hkvc.donate;

import com.sun.net.httpserver.HttpExchange;
import org.bouncycastle.crypto.generators.SCrypt;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;

final class Auth {
    final Store store;final String adminEmail;final String origin;
    final Map<String,long[]> attempts=new HashMap<>();
    Auth(Store store,String email,String password,String origin)throws Exception{
        this.store=store;adminEmail=email.trim().toLowerCase(Locale.ROOT);this.origin=origin;
        if(!adminEmail.matches("[^\\s@]+@[^\\s@]+\\.[^\\s@]+"))throw new IllegalArgumentException("Configure ADMIN_EMAIL");
        if(store.one("SELECT id FROM accounts WHERE role='admin'")==null){if(password.length()<12||password.startsWith("replace-"))throw new IllegalArgumentException("Configure INITIAL_ADMIN_PASSWORD with at least 12 characters");
            store.update("INSERT INTO accounts (id,email,password_hash,role) VALUES (?,?,?,'admin')",UUID.randomUUID().toString(),adminEmail,hash(password));}
    }
    static byte[] random(int size){byte[] b=new byte[size];new SecureRandom().nextBytes(b);return b;}
    static String digest(String token)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.UTF_8)));}
    static String hash(String password){String salt=HexFormat.of().formatHex(random(16));return salt+":"+HexFormat.of().formatHex(SCrypt.generate(password.getBytes(StandardCharsets.UTF_8),salt.getBytes(StandardCharsets.UTF_8),16384,8,1,64));}
    static boolean check(String password,String hash){try{String[] parts=hash.split(":");return MessageDigest.isEqual(HexFormat.of().parseHex(parts[1]),SCrypt.generate(password.getBytes(StandardCharsets.UTF_8),parts[0].getBytes(StandardCharsets.UTF_8),16384,8,1,64));}catch(Exception e){return false;}}
    String token(HttpExchange e){String cookie=e.getRequestHeaders().getFirst("Cookie");if(cookie!=null)for(String piece:cookie.split(";")){String v=piece.trim();if(v.matches("donate_session=[a-f0-9]{64}"))return v.substring(15);}return null;}
    Map<String,Object> user(HttpExchange e)throws Exception{String token=token(e);return token==null?null:store.one("SELECT a.id,a.role,a.donor_id,CASE WHEN a.role='admin' THEN a.email ELSE d.email END AS email FROM sessions s JOIN accounts a ON a.id=s.account_id LEFT JOIN donors d ON d.id=a.donor_id WHERE s.token_hash=? AND s.expires_at>? AND (a.role='admin' OR d.id IS NOT NULL)",digest(token),System.currentTimeMillis());}
    boolean admin(Map<String,Object> user){return user!=null&&"admin".equals(user.get("role"));}
    void sameOrigin(HttpExchange e){String expected=origin.isBlank()?"http://"+e.getRequestHeaders().getFirst("Host"):origin;if(!expected.equals(e.getRequestHeaders().getFirst("Origin")))throw new Application.Failure(403,"Invalid origin");}
    Map<String,Object> login(HttpExchange e,Map<String,Object> body)throws Exception{
        sameOrigin(e);String ip=e.getRemoteAddress().getAddress().getHostAddress();long now=System.currentTimeMillis();long[] attempt=attempts.get(ip);
        if(attempt!=null&&attempt[1]>now&&attempt[0]>=5)throw new Application.Failure(429,"Too many attempts. Try again in 15 minutes.");
        String email=Application.string(body,"email").trim().toLowerCase(Locale.ROOT),password=Application.string(body,"password");
        if(password.length()>256)throw new Application.Failure(401,"Invalid credentials");
        var a=store.one("SELECT a.* FROM accounts a LEFT JOIN donors d ON d.id=a.donor_id WHERE (a.role='admin' AND a.email=?) OR (a.role='donor' AND d.email=?)",email,email);
        boolean valid=check(password,a==null?"0".repeat(32)+":"+"0".repeat(128):(String)a.get("password_hash"));
        if(a==null||!valid){attempts.put(ip,new long[]{attempt!=null&&attempt[1]>now?attempt[0]+1:1,now+900000});if(attempts.size()>10000)attempts.values().removeIf(v->v[1]<now);throw new Application.Failure(401,"Invalid email or password");}
        attempts.remove(ip);String token=HexFormat.of().formatHex(random(32));store.update("DELETE FROM sessions WHERE expires_at<=?",now);store.update("INSERT INTO sessions VALUES (?,?,?)",digest(token),a.get("id"),now+7*86400000L);
        e.getResponseHeaders().set("Set-Cookie","donate_session="+token+"; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800"+(origin.startsWith("https://")?"; Secure":""));
        return Application.map("user",Application.map("id",a.get("id"),"email",email,"role",a.get("role")));
    }
    void logout(HttpExchange e)throws Exception{String token=token(e);if(token!=null)store.update("DELETE FROM sessions WHERE token_hash=?",digest(token));e.getResponseHeaders().set("Set-Cookie","donate_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"+(origin.startsWith("https://")?"; Secure":""));}
    Map<String,Object> provision(Map<String,Object> body)throws Exception{
        var d=store.one("SELECT id,email FROM donors WHERE id=?",Application.string(body,"donorId"));if(d==null)throw new Application.Failure(404,"Donor not found");
        if(adminEmail.equals(d.get("email")))throw new Application.Failure(409,"Administrator email cannot be used for a donor login");
        var old=store.one("SELECT id FROM accounts WHERE donor_id=?",d.get("id"));String id=old==null?UUID.randomUUID().toString():(String)old.get("id"),password=Base64.getUrlEncoder().withoutPadding().encodeToString(random(18));
        store.transaction(()->{store.update("INSERT INTO accounts (id,email,password_hash,role,donor_id) VALUES (?,?,?,'donor',?) ON CONFLICT(donor_id) DO UPDATE SET email=excluded.email,password_hash=excluded.password_hash",id,d.get("email"),hash(password),d.get("id"));
            store.update("DELETE FROM sessions WHERE account_id=?",id);store.update("UPDATE donors SET user_id=? WHERE id=?",id,d.get("id"));return null;});return Application.map("email",d.get("email"),"password",password);
    }
}
