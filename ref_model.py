# Python reference model: executes program.hex with RV32IM semantics (independent check of encodings + expected values)
M=0xFFFFFFFF
def s(x): return x-(1<<32) if x&0x80000000 else x
def sx(v,b): return v-(1<<b) if v&(1<<(b-1)) else v
prog=[int(l,16) for l in open('program.hex').read().split()]
r=[0]*32; mem={}; pc=0
for _ in range(60):
    i=prog[pc//4] if pc//4<len(prog) else 0x13
    op=i&0x7f; rd=(i>>7)&31; f3=(i>>12)&7; rs1=(i>>15)&31; rs2=(i>>20)&31; f7=i>>25
    a,b=r[rs1],r[rs2]; npc=pc+4; w=None
    if op==0x33:
        if f7==1:
            if f3==0: w=(a*b)&M
            elif f3==4: w=M if b==0 else (int(s(a)/s(b)))&M
            elif f3==6: w=a if b==0 else (s(a)-int(s(a)/s(b))*s(b))&M
        elif f3==0: w=(a-b)&M if f7==0x20 else (a+b)&M
    elif op==0x13 and f3==0: w=(a+sx(i>>20,12))&M
    elif op==0x23: mem[(a+sx(((i>>25)<<5)|rd,12))&M]=b
    elif op==0x03: w=mem.get((a+sx(i>>20,12))&M,0)
    elif op==0x6f: 
        if i==0x6f: break
    if w is not None and rd: r[rd]=w
    pc=npc
exp={1:20,2:6,3:26,4:14,5:120,6:3,7:2,8:26,9:28,10:M}
ok=True
for k,v in exp.items():
    print(f"x{k} = {s(r[k])}", "OK" if r[k]==v else f"MISMATCH (exp {s(v)})"); ok&=r[k]==v
print("REFERENCE MODEL:", "all match" if ok else "FAILED")
