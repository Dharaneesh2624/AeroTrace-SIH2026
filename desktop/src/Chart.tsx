import {useEffect,useRef} from 'react';
import * as echarts from 'echarts/core';
import {LineChart} from 'echarts/charts';
import {GridComponent,TooltipComponent,MarkLineComponent,DataZoomComponent,LegendComponent} from 'echarts/components';
import {CanvasRenderer} from 'echarts/renderers';
echarts.use([LineChart,GridComponent,TooltipComponent,MarkLineComponent,DataZoomComponent,LegendComponent,CanvasRenderer]);
type Series={name:string,color:string,data:(number|null)[]};
export default function Chart({labels,series,cursor,unit='',height=185}:{labels:(number|string)[],series:Series[],cursor?:number,unit?:string,height?:number}){
  const ref=useRef<HTMLDivElement>(null);const chart=useRef<echarts.ECharts|null>(null);
  useEffect(()=>{chart.current=echarts.init(ref.current!,null,{renderer:'canvas'});const ro=new ResizeObserver(()=>chart.current?.resize());ro.observe(ref.current!);return()=>{ro.disconnect();chart.current?.dispose();};},[]);
  useEffect(()=>{chart.current?.setOption({animation:false,backgroundColor:'transparent',textStyle:{fontFamily:'Segoe UI'},
    tooltip:{trigger:'axis',backgroundColor:'#101a29',borderColor:'#334559',textStyle:{color:'#dfe9f3'},valueFormatter:(v:unknown)=>typeof v==='number'?v.toFixed(2):'Unavailable'},
    grid:{left:48,right:18,top:20,bottom:34},legend:{show:series.length>1,top:0,textStyle:{color:'#a5b4c5'},itemWidth:12,itemHeight:3},
    xAxis:{type:'value',min:labels.length?Number(labels[0]):0,max:labels.length>1?Number(labels.at(-1)):1,axisLabel:{color:'#768aa2',fontSize:10},axisLine:{lineStyle:{color:'#26374a'}},axisTick:{show:false}},
    yAxis:{type:'value',scale:true,name:unit,nameTextStyle:{color:'#768aa2',fontSize:10},axisLabel:{color:'#768aa2',fontSize:10},splitLine:{lineStyle:{color:'#1d2d3f',type:'dashed'}}},
    series:series.map((s,i)=>({name:s.name,type:'line',data:s.data.map((value,index)=>[Number(labels[index]),value]),showSymbol:false,connectNulls:false,lineStyle:{width:1.8,color:s.color},itemStyle:{color:s.color},
      areaStyle:series.length===1?{color:s.color,opacity:.045}:undefined,
      markLine:cursor!==undefined&&i===0?{symbol:'none',silent:true,label:{show:false},lineStyle:{color:'#e5ad64',width:1,type:'dashed'},data:[{xAxis:cursor}]}:undefined}))},true);},[labels,series,cursor,unit]);
  return <div ref={ref} style={{height,width:'100%'}} aria-label="Telemetry chart"/>;
}
