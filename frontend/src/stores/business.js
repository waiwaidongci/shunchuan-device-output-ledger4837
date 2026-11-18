import {loadAll,loadQuarantine} from '../api/business.js';
export const store={session:JSON.parse(localStorage.getItem('session')||'null'),data:{sources:[],periods:[],policies:[],runs:[],schedules:[],deliveries:[],audits:[],quarantineMap:{}},selected:null};
export async function reload(){
 const data=await loadAll();
 data.quarantineMap=Object.fromEntries(await Promise.all(data.runs.map(r=>loadQuarantine(r.id).then(q=>[r.id,q]))));
 store.data=data;
}
export function setSession(value){store.session=value;if(value)localStorage.setItem('session',JSON.stringify(value));else localStorage.removeItem('session')}
