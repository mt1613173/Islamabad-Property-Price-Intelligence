"use client";
import { useState } from "react";
const sectors = ["G-10","G-11","G-13","G-14"];
const types = ["House","Plot","Apartment","Commercial"];

export function PropertyForm({ onSubmit, button="Submit", includeActual=false }: { onSubmit: (data:any)=>void; button?: string; includeActual?: boolean }) {
  const [form,setForm] = useState<any>({ sector:"G-13", prop_type:"House", size_marla:5, listing_age_days:7, is_professional:false, actual_price:2.5 });
  const set = (k:string,v:any)=>setForm((f:any)=>({...f,[k]:v}));
  return <div className="grid gap-4 md:grid-cols-2">
    {includeActual && <label className="text-sm font-bold">Actual Price (Crore)<input className="input mt-2" type="number" step="0.1" value={form.actual_price} onChange={e=>set("actual_price",Number(e.target.value))}/></label>}
    <label className="text-sm font-bold">Sector<select className="input mt-2" value={form.sector} onChange={e=>set("sector",e.target.value)}>{sectors.map(x=><option key={x}>{x}</option>)}</select></label>
    <label className="text-sm font-bold">Property Type<select className="input mt-2" value={form.prop_type} onChange={e=>set("prop_type",e.target.value)}>{types.map(x=><option key={x}>{x}</option>)}</select></label>
    <label className="text-sm font-bold">Size in Marla<input className="input mt-2" type="number" value={form.size_marla} onChange={e=>set("size_marla",Number(e.target.value))}/></label>
    <label className="text-sm font-bold">Listing Age Days<input className="input mt-2" type="number" value={form.listing_age_days} onChange={e=>set("listing_age_days",Number(e.target.value))}/></label>
    <label className="text-sm font-bold">Seller Type<select className="input mt-2" value={form.is_professional ? "Professional" : "Normal"} onChange={e=>set("is_professional",e.target.value==="Professional")}><option>Normal</option><option>Professional</option></select></label>
    <div className="md:col-span-2"><button className="btn-primary w-full" onClick={()=>onSubmit(form)}>{button}</button></div>
  </div>
}
