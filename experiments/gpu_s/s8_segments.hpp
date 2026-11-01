#pragma once
// Application-only synchronization boundaries. All streams on the selected device
// complete before a dependency is submitted. GPU activity time is never inferred
// from CPU wall time. Empty windows and verification copies receive no model time.
static std::ofstream segments;
static std::uint64_t activity_id=0, segment_id=0, window_start=0, window_activity=0;
static std::uint64_t fixed_segment_ps=1000;
static bool window_open=false;
static json compute_rows;
static std::size_t compute_cursor=0;
static void load_compute_table(const json& config) {
    std::ifstream f(config.at("compute_table_path").get<std::string>());
    need(bool(f),"Cannot read qualified compute table");json table;f>>table;
    need(table.at("header")==config.at("expected_compute_header"),"Compute header mismatch");
    need(table.at("header").at("frozen_G1")==true,"Compute table not frozen");
    compute_rows=table.at("segments");need(compute_rows.size()==18072,"Compute table segment count mismatch");
    for(std::size_t i=0;i<compute_rows.size();++i) {
        const auto& r=compute_rows.at(i);
        need(r.at("segment_id")==i+1,"Missing/duplicate/reordered compute segment");
        need(r.at("duration_ps").is_number_unsigned(),"Invalid integer compute duration");
    }
}
static void finish_compute_table() {need(compute_cursor==compute_rows.size(),"Unconsumed compute segments");}

static void segment_begin() {
    need(!window_open,"Overlapping segment windows");
    window_start=stamp();window_activity=activity_id;window_open=true;
}
static void segment_end(const char* kind,std::uint64_t node) {
    need(window_open,"Missing segment start");
    need(cudaDeviceSynchronize()==cudaSuccess,"Segment GPU synchronization failed");
    const auto end=stamp();
    need(cuptiActivityFlushAll(0)==CUPTI_SUCCESS,"Segment CUPTI flush failed");
    std::lock_guard<std::mutex> guard(kernel_mutex);
    const bool verification=std::string(kind)=="verification";
    const auto count=activity_id-window_activity;
    std::uint64_t duration=0,table_id=0;
    if(!verification) {
        need(compute_cursor<compute_rows.size(),"Extra GPU segment outside compute table");
        const auto& expected=compute_rows.at(compute_cursor++);
        need(expected.at("kind")==kind&&expected.at("node_id")==node&&expected.at("step")==step.load(),"Compute segment boundary mismatch");
        duration=expected.at("duration_ps").get<std::uint64_t>();table_id=expected.at("segment_id");
        need((count>0)==(duration>0),"Actual GPU activity coverage differs from frozen table");
    }
    json row={{"segment_id",++segment_id},{"kind",kind},{"node_id",node},{"step",step.load()},
              {"start_ns",window_start},{"end_ns",end},{"first_activity_id",window_activity+1},
              {"activity_count",count},{"modeled",!verification&&count>0},{"duration_ps",duration}};
    row["table_segment_id"]=verification?json(nullptr):json(table_id);
    if(gate&&!verification&&count)row["advance"]=gate->advance_segment(duration);
    segments<<row.dump()<<'\n';need(bool(segments),"Segment record write failed");window_open=false;
}
