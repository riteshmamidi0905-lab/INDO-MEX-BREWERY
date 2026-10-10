#!/usr/bin/env python3
"""GLS profile guides (NOT renders). Parametric 2-D outlines of the canonical ring-collar glass family from LOCKED-SCENE-DNA section 8, drawn to scale
with dimension labels, to give an image generator exact proportions. Units: centimetres. Run from repo root -> visuals/generated/GLS-inputs/."""
import os
from PIL import Image, ImageDraw, ImageFont
_orig_text=ImageDraw.ImageDraw.text
def _text(self,*a,**k):
    if ANNOT: return _orig_text(self,*a,**k)
ImageDraw.ImageDraw.text=_text
OUT="visuals/generated/GLS-inputs"; PX=32; ANNOT=True  # px per cm
# (z_cm, outer_diameter_cm) profiles, base at z=0
HEFE=[(0,5.6),(1.0,5.6),(1.1,5.5),(4,5.4),(8,5.6),(12,6.1),(16,6.7),(20,7.3),(24.5,7.9)]
LAGER=[(0,5.2),(0.9,5.2),(1.0,5.1),(10,6.0),(20,7.2)]
RESERVE_BOWL=[(7,3.0),(9,5.4),(11,6.2),(12.2,6.4),(12.4,5.8),(13.5,6.5),(17,6.9)]
FLIGHT=[(0,3.6),(0.8,3.6),(1.0,3.0),(3,3.6),(6,5.0),(8,5.2),(10,4.6)]
def font(sz):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",sz)
    except Exception: return ImageFont.load_default()
def interp(p,z):
    for (z0,d0),(z1,d1) in zip(p,p[1:]):
        if z0<=z<=z1: return d0+(d1-d0)*(0 if z1==z0 else (z-z0)/(z1-z0))
    return p[-1][1]
def draw_glass(dr,cx,base_y,prof,ring_z,ring_h=1.2,ring_proud=0.5,stem=None,label=""):
    zmax=prof[-1][0]; pts=[(cx-d/2*PX,base_y-z*PX) for z,d in prof]; pts_r=[(cx+d/2*PX,base_y-z*PX) for z,d in prof]
    outline=pts+pts_r[::-1]; dr.polygon(outline,fill=(232,238,240),outline=(30,30,30))
    d=interp(prof,ring_z); r=d/2+ring_proud
    dr.rounded_rectangle([cx-r*PX,base_y-(ring_z+ring_h)*PX,cx+r*PX,base_y-ring_z*PX],radius=6,fill=(200,215,222),outline=(30,30,30),width=2)
    dr.text((cx-60,base_y+14),label,fill=(0,0,0),font=font(20))
    if ANNOT: dr.line([(cx+prof[-1][1]/2*PX+40,base_y),(cx+prof[-1][1]/2*PX+40,base_y-zmax*PX)],fill=(120,0,0),width=2)
    dr.text((cx+prof[-1][1]/2*PX+48,base_y-zmax*PX/2),f"{zmax:g} cm",fill=(120,0,0),font=font(20))
    dr.text((cx+r*PX+8,base_y-(ring_z+ring_h/2)*PX-10),f"ring {ring_z:g}-{ring_z+ring_h:g} cm",fill=(0,0,120),font=font(16))
def sheet_single():
    im=Image.new("RGB",(1400,1000),(250,248,244)); dr=ImageDraw.Draw(im)
    draw_glass(dr,450,900,HEFE,6.0,label="Collar Weizen (GLS-01), 24.5 cm, ~0.5 L beer + head")
    dr.text((30,20),"PROFILE GUIDE, NOT A PHOTO. Clear colourless glass, no print. Ring ~5 mm proud, ~12 mm tall, rounded, one-quarter up (~6 cm), never wider than the rim (7.9 cm).",fill=(0,0,0),font=font(18))
    dr.text((30,50),f"Base 5.6 cm, thick clear base ~1 cm, waist ~6.1 cm at ~12 cm, rim 7.9 cm fine (~1.5 mm). Do not render these annotations.",fill=(0,0,0),font=font(18))
    im.save(f"{OUT}/GLS-01-profile-guide{'' if ANNOT else '-clean'}.png")
def sheet_family():
    im=Image.new("RGB",(1800,1000),(250,248,244)); dr=ImageDraw.Draw(im); by=870
    draw_glass(dr,260,by,HEFE,6.0,label="Collar Weizen 24.5 cm")
    draw_glass(dr,640,by,LAGER,5.0,label="Collar Lager 20 cm")
    # reserve goblet: foot, stem, stepped bowl
    cx=1020; prof=[(0,5.0),(0.6,5.0),(1.0,1.2),(7,1.0)]+RESERVE_BOWL
    zmax=prof[-1][0]; L=[(cx-d/2*PX,by-z*PX) for z,d in prof]; R=[(cx+d/2*PX,by-z*PX) for z,d in prof]
    dr.polygon(L+R[::-1],fill=(232,238,240),outline=(30,30,30))
    r=interp(prof,7.4)/2+0.5; dr.rounded_rectangle([cx-r*PX,by-8.2*PX,cx+r*PX,by-7.0*PX],radius=6,fill=(200,215,222),outline=(30,30,30),width=2)
    dr.text((cx-70,by+14),"Stepwell Goblet 17 cm",fill=(0,0,0),font=font(16))
    draw_glass(dr,1500,by,FLIGHT,2.5,ring_h=1.0,ring_proud=0.4,label="Collar Tulip 10 cm")
    dr.text((30,20),"FAMILY PROFILE GUIDE (to scale), NOT A PHOTO. Same raised ring on all four; ring never wider than the rim. Heights 24.5 > 20 > 17 > 10 cm. Do not render annotations.",fill=(0,0,0),font=font(20))
    im.save(f"{OUT}/GLS-02-family-profile-guide{'' if ANNOT else '-clean'}.png")
if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)
    for ANNOT in (True,False): sheet_single(); sheet_family()
    print("ok")
