package org.hkvc.donate;

import java.util.*;
import static org.hkvc.donate.Application.*;

/** Fixed campaign requirements, independently enforced on the server. */
final class LeafRules {
    static final String CATEGORY="gift66e7d1f75cda4ddd93ef092ecfa59178";
    static boolean isLeaf(String category){return CATEGORY.equals(category);}
    static int validate(Map<String,Object> submitted,Map<String,Object> fields,String donorId,Store store)throws Exception{
        String mode=string(submitted,"leafMode"),name=string(submitted,"leafName").trim(),layout=string(submitted,"leafLayout");
        Validation.require(List.of("zh","en","logo").contains(mode),"請選擇中文、英文或 Logo / Choose Chinese, English or Logo");
        Validation.require(List.of("multiple","larger").contains(layout),"請選擇紀念葉形式 / Choose the leaf arrangement");
        int quantity;try{quantity=Integer.parseInt(string(submitted,"leafQuantity"));}catch(Exception ex){throw new Failure(400,"請填寫整數數量 / Enter a whole quantity");}
        Validation.require(quantity>=1&&quantity<=10000,"Invalid leaf quantity");
        if(mode.equals("logo")){
            String key=string(submitted,"leafLogo");
            Validation.require(key.matches("[0-9a-f-]{36}\\.(png|jpg)")&&java.nio.file.Files.isRegularFile(store.object("leaf-logos/"+donorId+"/"+key)),"請上傳 PNG 或 JPG Logo / Upload a PNG or JPG logo");
            fields.put("leafLogo",field("Logo 檔案","Logo file","/api/leaf-logo?donorId="+donorId+"&key="+key));
        }else{
            int count=name.codePointCount(0,name.length()),max=mode.equals("zh")?14:38;
            Validation.require(count>=1&&count<=max,"姓名超出字數限制 / Name exceeds the character limit");
            boolean valid=mode.equals("en")?name.matches("[\\x20-\\x7E]+")&&name.matches(".*[A-Za-z].*"):name.matches("[\\p{IsHan}\\p{P}0-9 ]+")&&name.codePoints().anyMatch(c->Character.UnicodeScript.of(c)==Character.UnicodeScript.HAN);
            Validation.require(valid,mode.equals("en")?"只可輸入英文、數字、空格及標點（最多 38 字元） / English letters, numbers, spaces and punctuation only (max 38 characters)":"只可輸入中文、數字、空格及標點（最多 14 字） / Chinese, numbers, spaces and punctuation only (max 14 characters)");
            fields.put("leafName",field("紀念葉展示姓名","Name displayed on the leaf",name));
        }
        fields.put("leafMode",field("展示內容","Personalisation",map("zh",mode.equals("zh")?"中文姓名":mode.equals("en")?"英文姓名":"Logo","en",mode.equals("zh")?"Chinese name":mode.equals("en")?"English name":"Logo")));
        fields.put("leafLayout",field("紀念葉形式","Leaf arrangement",map("zh",layout.equals("multiple")?quantity+" 片紀念葉（相同內容）":"1 片較大紀念葉（使用 "+quantity+" 次權益）","en",layout.equals("multiple")?quantity+" leaves (same personalisation)":"1 larger leaf (uses "+quantity+" allowances)")));
        return quantity;
    }
}
