#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <portaudio.h>

#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <atomic>
#include <memory>
#include <algorithm>
#include <mutex>
#include <map>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace py = pybind11;

// --- Structs and helper functions should be defined before use ---

struct DeviceInfo {
    int index;
    std::string name;
    int maxOutputChannels;
};

void pa_check_error(PaError err, const std::string& message) {
    if (err != paNoError) {
        throw std::runtime_error(message + ": " + Pa_GetErrorText(err));
    }
}

void initialize() {
    pa_check_error(Pa_Initialize(), "Failed to initialize PortAudio");
    py::print("PortAudio initialized.");
}

void terminate() {
    Pa_Terminate();
    py::print("PortAudio terminated.");
}

std::vector<DeviceInfo> getDeviceDetails() {
    std::vector<DeviceInfo> deviceDetails;
    int numDevices = Pa_GetDeviceCount();
    if (numDevices < 0) pa_check_error(numDevices, "Failed to get device count");
    for (int i = 0; i < numDevices; ++i) {
        const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo(i);
        if (deviceInfo) {
            // This line now works because DeviceInfo is a complete type
            deviceDetails.push_back({i, std::string(deviceInfo->name), deviceInfo->maxOutputChannels});
        }
    }
    return deviceDetails;
}


class Synth : public std::enable_shared_from_this<Synth> {
private:
    std::atomic<bool> is_playing_{false};
    double phase_{0.0};
    double sample_rate_;
    double amplitude_;
    double phase_increment_{0.0};
    double frequency_;

public:
    Synth(double sample_rate) : 
        sample_rate_(sample_rate), 
        amplitude_(0.5), 
        frequency_(440.0) 
    {
        setFrequency(this->frequency_);
    }
    virtual ~Synth() = default;

    Synth(const Synth&) = delete;
    Synth& operator=(const Synth&) = delete;

    void render(float* mono_out, unsigned long frames) {
        for (unsigned long i = 0; i < frames; ++i) {
            mono_out[i] = static_cast<float>(this->amplitude_ * std::sin(this->phase_));
            this->phase_ += this->phase_increment_;
            if (this->phase_ >= 2.0 * M_PI) {
                this->phase_ -= 2.0 * M_PI;
            }
        }
    }

    void start() { is_playing_.store(true); }
    void stop() { is_playing_.store(false); }
    bool isPlaying() const { return is_playing_.load(); }

    void setFrequency(double freq) {
        this->frequency_ = freq;
        this->phase_increment_ = (2.0 * M_PI * this->frequency_) / this->sample_rate_;
    }
    double getFrequency() const { return frequency_; }
};


class Patch : public std::enable_shared_from_this<Patch> {
private:
    std::string synth_name_;
    std::vector<int> channels_;

public:
    Patch(std::string synth_name, std::vector<int> channels) 
        : synth_name_(std::move(synth_name)), channels_(std::move(channels)) {}
    ~Patch() = default;

    const std::string& getSynthName() const { return synth_name_; }
    const std::vector<int>& getChannels() const { return channels_; }
};


class AudioEngine {
private:
    PaStream* stream_{nullptr};
    double sample_rate_;
    int numOutputChannels_{0};
    
    std::map<std::string, std::shared_ptr<Synth>> synths_;
    std::map<std::string, std::shared_ptr<Patch>> patches_;
    
    std::recursive_mutex engine_mutex_;
    
    std::vector<std::string> synth_names_to_delete_;
    std::vector<std::string> patch_names_to_delete_;

    void _cleanup() {
        std::vector<std::string> synth_names_to_process;
        std::vector<std::string> patch_names_to_process;
        {
            std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
            if (synth_names_to_delete_.empty() && patch_names_to_delete_.empty()) return;
            
            synth_names_to_process.swap(synth_names_to_delete_);
            patch_names_to_process.swap(patch_names_to_delete_);
        }

        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);

        for (const auto& name : patch_names_to_process) {
            patches_.erase(name);
        }

        for (const auto& synth_name : synth_names_to_process) {
            std::vector<std::string> related_patches_to_delete;
            for (const auto& [patch_name, patch_ptr] : patches_) {
                if (patch_ptr->getSynthName() == synth_name) {
                    related_patches_to_delete.push_back(patch_name);
                }
            }
            for (const auto& patch_name : related_patches_to_delete) {
                patches_.erase(patch_name);
            }
            synths_.erase(synth_name);
        }
    }

    int paCallback(const void* inputBuffer, void* outputBuffer,
                   unsigned long framesPerBuffer,
                   const PaStreamCallbackTimeInfo* timeInfo,
                   PaStreamCallbackFlags statusFlags) {
        
        _cleanup();

        auto* out = static_cast<float*>(outputBuffer);
        std::fill_n(out, framesPerBuffer * this->numOutputChannels_, 0.0f);
        
        std::vector<float> mono_buffer(framesPerBuffer);
        
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        
        for (const auto& [patch_name, patch_ptr] : patches_) {
            auto synth_it = synths_.find(patch_ptr->getSynthName());
            if (synth_it != synths_.end() && synth_it->second->isPlaying()) {
                std::shared_ptr<Synth> synth = synth_it->second;
                synth->render(mono_buffer.data(), framesPerBuffer);
                
                for (int channel_index : patch_ptr->getChannels()) {
                    if (channel_index < this->numOutputChannels_) {
                        for (unsigned long frame = 0; frame < framesPerBuffer; ++frame) {
                            out[frame * this->numOutputChannels_ + channel_index] += mono_buffer[frame];
                        }
                    }
                }
            }
        }
        return paContinue;
    }

    static int paCallbackAdapter(const void* inputBuffer, void* outputBuffer,
                                 unsigned long framesPerBuffer,
                                 const PaStreamCallbackTimeInfo* timeInfo,
                                 PaStreamCallbackFlags statusFlags,
                                 void* userData) {
        return static_cast<AudioEngine*>(userData)->paCallback(inputBuffer, outputBuffer, framesPerBuffer, timeInfo, statusFlags);
    }

public:
    AudioEngine(int deviceIndex, int numChannels) : numOutputChannels_(numChannels) {
        const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo(deviceIndex);
        if (deviceInfo == nullptr) throw std::runtime_error("Invalid device index");
        if (numChannels > deviceInfo->maxOutputChannels) {
            throw std::runtime_error("Device does not support requested number of output channels");
        }
        
        this->sample_rate_ = deviceInfo->defaultSampleRate;
        py::print("Device reports default sample rate of: ", this->sample_rate_);

        PaStreamParameters outputParameters;
        outputParameters.device = deviceIndex;
        outputParameters.channelCount = numChannels;
        outputParameters.sampleFormat = paFloat32;
        outputParameters.suggestedLatency = Pa_GetDeviceInfo(deviceIndex)->defaultLowOutputLatency;
        outputParameters.hostApiSpecificStreamInfo = nullptr;

        pa_check_error(
            Pa_OpenStream(&this->stream_, nullptr, &outputParameters, this->sample_rate_, 
                          paFramesPerBufferUnspecified, paNoFlag, paCallbackAdapter, this),
            "Failed to open PortAudio stream"
        );
        pa_check_error(Pa_StartStream(this->stream_), "Failed to start PortAudio stream");
        py::print("PortAudio stream started on '", deviceInfo->name, "' with ", numChannels, " channels.");
    }

    ~AudioEngine() {
        if (stream_) {
            Pa_StopStream(stream_);
            Pa_CloseStream(stream_);
        }
        py::print("AudioEngine instance destroyed. Stream stopped and closed.");
    }

    std::shared_ptr<Synth> synth(const std::string& name) {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        auto it = synths_.find(name);
        if (it != synths_.end()) {
            return it->second;
        } else {
            auto new_synth = std::make_shared<Synth>(this->sample_rate_);
            synths_[name] = new_synth;
            return new_synth;
        }
    }

    std::shared_ptr<Patch> patch(const std::string& patch_name, const std::string& synth_name, std::vector<int> channels) {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        if (synths_.find(synth_name) == synths_.end()) {
            throw std::runtime_error("Cannot create patch: synth with name '" + synth_name + "' does not exist.");
        }

        auto it = patches_.find(patch_name);
        if (it != patches_.end()) {
            return it->second;
        } else {
            auto new_patch = std::make_shared<Patch>(synth_name, channels);
            patches_[patch_name] = new_patch;
            return new_patch;
        }
    }

    void delete_synth(const std::string& name) {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        synth_names_to_delete_.push_back(name);
    }

    void delete_patch(const std::string& name) {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        patch_names_to_delete_.push_back(name);
    }
};


PYBIND11_MODULE(oscar_server, m) {
    m.doc() = "A live-coding audio engine with named synths and patches";
    
    m.def("initialize", &initialize, "Initializes the PortAudio library. Must be called first.");
    m.def("terminate", &terminate, "Terminates the PortAudio library. Must be called last.");
    m.def("get_device_details", &getDeviceDetails, "Gets a list of all available audio devices.");

    py::class_<DeviceInfo>(m, "DeviceInfo")
        .def_readonly("index", &DeviceInfo::index)
        .def_readonly("name", &DeviceInfo::name)
        .def_readonly("max_output_channels", &DeviceInfo::maxOutputChannels)
        .def("__repr__", [](const DeviceInfo &d) {
            return "<DeviceInfo " + std::to_string(d.index) + ": '" + d.name + "' ("
                   + std::to_string(d.maxOutputChannels) + " channels)>";
        });

    py::class_<Synth, std::shared_ptr<Synth>>(m, "Synth")
        .def("start", &Synth::start)
        .def("stop", &Synth::stop)
        .def("is_playing", &Synth::isPlaying)
        .def("set_frequency", &Synth::setFrequency)
        .def("get_frequency", &Synth::getFrequency);
    
    py::class_<Patch, std::shared_ptr<Patch>>(m, "Patch")
        .def("get_channels", &Patch::getChannels)
        .def("get_synth_name", &Patch::getSynthName);

    py::class_<AudioEngine>(m, "AudioEngine")
        .def(py::init<int, int>(), py::arg("device_index"), py::arg("num_channels"))
        .def("synth", &AudioEngine::synth, py::arg("name"), "Gets or creates a synth by its unique name.")
        .def("patch", &AudioEngine::patch, py::arg("patch_name"), py::arg("synth_name"), py::arg("channels"), "Gets or creates a patch to route a synth to channels.")
        .def("delete_synth", &AudioEngine::delete_synth, py::arg("name"), "Schedules a named synth and its associated patches for deletion.")
        .def("delete_patch", &AudioEngine::delete_patch, py::arg("name"), "Schedules a named patch for deletion.");
}